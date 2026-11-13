"""Fast lifecycle tests for architecture-specific hook behavior."""

from pathlib import Path
import sys
from types import SimpleNamespace

import pytest
import torch
from torch import nn

from instrumentation.adapters import HeadPatch, ModulePatch, Qwen2ModelAdapter
from instrumentation.model_adapter import ComponentSite


class DummyAttention(nn.Module):
    """Attention-shaped fixture exposing a pre-projection head tensor."""

    def __init__(self) -> None:
        super().__init__()
        self.config = SimpleNamespace(num_attention_heads=2)
        self.head_dim = 1
        self.o_proj = nn.Linear(2, 2, bias=False)

    def forward(self, tensor: torch.Tensor) -> torch.Tensor:
        return self.o_proj(tensor)


class DummyBlock(nn.Module):
    """Minimal Qwen-shaped block for hook lifecycle tests."""

    def __init__(self) -> None:
        super().__init__()
        self.self_attn = DummyAttention()
        self.mlp = nn.Linear(2, 2, bias=False)

    def forward(self, tensor: torch.Tensor) -> torch.Tensor:
        return tensor + self.self_attn(tensor) + self.mlp(tensor)


def adapter_with_dummy_model() -> Qwen2ModelAdapter:
    """Create an unloaded adapter backed by a local Qwen-shaped fixture."""
    adapter = Qwen2ModelAdapter("fixture", "fixture", Path(".cache"))
    adapter.model = SimpleNamespace(model=SimpleNamespace(layers=[DummyBlock()]))
    return adapter


def test_passive_hook_is_read_only_and_removed() -> None:
    adapter = adapter_with_dummy_model()
    site = ComponentSite("L0.mlp_output", 0, "mlp_output", "fixture MLP output")
    inputs = torch.ones(1, 1, 2)
    baseline = adapter.model.model.layers[0](inputs)
    adapter.install_capture_hooks([site])
    observed = adapter.model.model.layers[0](inputs)
    assert torch.equal(baseline, observed)
    assert site.component_id in adapter.activations
    with pytest.raises(RuntimeError, match="already installed"):
        adapter.install_capture_hooks([site])
    adapter.remove_hooks()
    adapter.remove_hooks()
    assert not adapter._handles


def test_zero_intervention_changes_output_and_can_be_disabled() -> None:
    adapter = adapter_with_dummy_model()
    site = ComponentSite("L0.mlp_output", 0, "mlp_output", "fixture MLP output")
    inputs = torch.ones(1, 1, 2)
    baseline = adapter.model.model.layers[0](inputs)
    adapter.install_zero_intervention(site)
    intervened = adapter.model.model.layers[0](inputs)
    assert not torch.equal(baseline, intervened)
    adapter.remove_hooks()
    restored = adapter.model.model.layers[0](inputs)
    assert torch.equal(baseline, restored)


def test_activation_patch_is_step_aware_and_hooks_are_removed() -> None:
    adapter = adapter_with_dummy_model()
    site = ComponentSite("L0.mlp_output", 0, "mlp_output", "fixture MLP output")
    inputs = torch.ones(1, 3, 2)
    source = torch.full((1, 3, 2), 4.0)
    adapter.install_activation_patch(site, source, [2])
    adapter.model.model.layers[0](inputs)
    assert adapter.intervention_applications == 1
    adapter.model.model.layers[0](torch.ones(1, 1, 2))
    assert adapter.intervention_applications == 1
    adapter.remove_hooks()
    assert adapter._handles == []


def test_position_zero_intervention_is_local_and_removed() -> None:
    adapter = adapter_with_dummy_model()
    site = ComponentSite("L0.mlp_output", 0, "mlp_output", "fixture MLP output")
    inputs = torch.ones(1, 3, 2)
    baseline = adapter.model.model.layers[0](inputs)
    adapter.install_zero_intervention_at_positions(site, [2])
    changed = adapter.model.model.layers[0](inputs)
    assert adapter.intervention_applications == 1
    assert torch.equal(baseline[:, :2], changed[:, :2])
    assert not torch.equal(baseline[:, 2:], changed[:, 2:])
    adapter.remove_hooks()
    assert adapter._handles == []


def test_generation_step_patch_fires_only_at_declared_step_and_cleans_up() -> None:
    adapter = adapter_with_dummy_model()
    site = ComponentSite("L0.mlp_output", 0, "mlp_output", "fixture MLP output")
    inputs = torch.ones(1, 3, 2)
    source = torch.full((1, 2), 7.0)
    adapter.install_generation_step_patch(site, source, target_step=1)
    adapter._active_generation_step = 0
    unchanged = adapter.model.model.layers[0](inputs)
    adapter._active_generation_step = 1
    changed = adapter.model.model.layers[0](inputs)
    assert adapter.intervention_applications == 1
    assert adapter.generation_hook_events == [{"step": 1, "sequence_length": 3}]
    assert not torch.equal(unchanged[:, -1], changed[:, -1])
    adapter.remove_hooks()
    adapter._active_generation_step = None
    assert adapter._handles == []
    adapter.install_generation_step_patch(site, source, target_step=1)
    adapter.remove_hooks()
    assert adapter._handles == []


def test_last_token_patch_accepts_stored_final_state_and_is_local() -> None:
    adapter = adapter_with_dummy_model()
    site = ComponentSite("L0.mlp_output", 0, "mlp_output", "fixture MLP output")
    inputs = torch.ones(1, 3, 2)
    baseline = adapter.model.model.layers[0](inputs)
    adapter.install_last_token_patch(site, torch.full((1, 2), 8.0))
    changed = adapter.model.model.layers[0](inputs)
    assert adapter.intervention_applications == 1
    assert torch.equal(baseline[:, :2], changed[:, :2])
    assert not torch.equal(baseline[:, 2], changed[:, 2])
    adapter.remove_hooks()
    with pytest.raises(ValueError, match=r"shape \[batch, hidden\]"):
        adapter.install_last_token_patch(site, torch.ones(1, 1, 2))


def test_generation_position_patch_is_step_and_position_local() -> None:
    adapter = adapter_with_dummy_model()
    site = ComponentSite("L0.mlp_output", 0, "mlp_output", "fixture MLP output")
    inputs = torch.ones(1, 3, 2)
    source = torch.full((1, 3, 2), 6.0)
    adapter.install_generation_position_patch(site, source, target_step=0, token_position=1)
    adapter._active_generation_step = 1
    baseline = adapter.model.model.layers[0](inputs)
    adapter._active_generation_step = 0
    changed = adapter.model.model.layers[0](inputs)
    assert adapter.intervention_applications == 1
    assert torch.equal(baseline[:, 0], changed[:, 0])
    assert not torch.equal(baseline[:, 1], changed[:, 1])
    assert torch.equal(baseline[:, 2], changed[:, 2])
    adapter.remove_hooks()
    adapter._active_generation_step = None


def test_head_capture_reconstructs_concat_and_head_patch_is_local() -> None:
    adapter = adapter_with_dummy_model()
    attention = adapter.model.model.layers[0].self_attn
    inputs = torch.tensor([[[1.0, 2.0], [3.0, 4.0]]])
    baseline = attention(inputs)
    adapter.install_head_capture(0)
    observed = attention(inputs)
    concat = adapter.head_activations["L0.pre_o_proj_concat"]
    heads = adapter.head_activations["L0.pre_o_proj_heads"]
    assert torch.equal(observed, baseline)
    assert torch.equal(heads.reshape_as(concat), concat)
    adapter.remove_hooks()
    adapter.install_head_patch(0, head=1, source=torch.tensor([[9.0]]), token_position=1)
    changed = attention(inputs)
    assert adapter.intervention_applications == 1
    assert torch.equal(changed[:, 0], baseline[:, 0])
    assert not torch.equal(changed[:, 1], baseline[:, 1])
    adapter.remove_hooks()
    assert adapter._handles == []


def test_comprehensive_capture_collects_modules_and_heads_in_one_pass() -> None:
    adapter = adapter_with_dummy_model()
    sites = adapter.identify_components([0])
    selected = [site for site in sites if site.component_type in {"attention_output", "mlp_output"}]
    inputs = torch.tensor([[[1.0, 2.0], [3.0, 4.0]]])
    baseline = adapter.model.model.layers[0](inputs)
    adapter.install_comprehensive_capture(selected, [0])
    observed = adapter.model.model.layers[0](inputs)
    assert torch.equal(baseline, observed)
    assert set(adapter.activations) == {site.component_id for site in selected}
    assert adapter.head_activations["L0.pre_o_proj_heads"].shape == (1, 2, 2, 1)
    with pytest.raises(RuntimeError, match="remove existing hooks"):
        adapter.install_comprehensive_capture(selected, [0])
    adapter.remove_hooks()
    assert adapter._handles == []


def test_composite_patch_applies_distinct_module_and_head_exactly_once() -> None:
    adapter = adapter_with_dummy_model()
    block = adapter.model.model.layers[0]
    site = ComponentSite("L0.mlp_output", 0, "mlp_output", "fixture MLP output")
    inputs = torch.tensor([[[1.0, 2.0], [3.0, 4.0]]])
    baseline = block(inputs)
    adapter.install_multi_patch(
        module_patches=[ModulePatch("receiver.module.L0.mlp", site, torch.tensor([[8.0, 8.0]]))],
        head_patches=[HeadPatch("receiver.head.L0.H1", 0, 1, torch.tensor([[9.0]]))],
    )
    changed = block(inputs)
    assert not torch.equal(changed, baseline)
    assert adapter.intervention_application_counts == {
        "receiver.module.L0.mlp": 1,
        "receiver.head.L0.H1": 1,
    }
    assert adapter.intervention_applications == 2
    adapter.remove_hooks()


def test_composite_patch_rejects_duplicate_addresses_before_execution() -> None:
    adapter = adapter_with_dummy_model()
    site = ComponentSite("L0.mlp_output", 0, "mlp_output", "fixture MLP output")
    with pytest.raises(ValueError, match="addresses must be unique"):
        adapter.install_multi_patch(module_patches=[
            ModulePatch("duplicate", site, torch.ones(1, 2)),
            ModulePatch("duplicate", site, torch.ones(1, 2)),
        ])
    assert adapter._handles == []


def test_load_forwards_cpu_memory_saving_option(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, dict[str, object]] = {}

    class FakeTokenizer:
        @classmethod
        def from_pretrained(cls, *_args: object, **_kwargs: object) -> "FakeTokenizer":
            return cls()

    class FakeModel(nn.Linear):
        def __init__(self) -> None:
            super().__init__(1, 1)

    class FakeAutoModel:
        @classmethod
        def from_pretrained(cls, *_args: object, **kwargs: object) -> FakeModel:
            calls["model"] = dict(kwargs)
            return FakeModel()

    monkeypatch.setitem(
        sys.modules,
        "transformers",
        SimpleNamespace(AutoModelForCausalLM=FakeAutoModel, AutoTokenizer=FakeTokenizer),
    )
    adapter = Qwen2ModelAdapter(
        "fixture", "revision", Path(".cache"), dtype=torch.float32, device="cpu",
        local_files_only=True, low_cpu_mem_usage=True,
    )
    adapter.load()
    assert calls["model"]["low_cpu_mem_usage"] is True
    assert calls["model"]["dtype"] is torch.float32
    assert calls["model"]["attn_implementation"] == "eager"
    assert adapter.model is not None and adapter.model.training is False
