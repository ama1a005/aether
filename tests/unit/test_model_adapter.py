"""Fast lifecycle tests for architecture-specific hook behavior."""

from pathlib import Path
from types import SimpleNamespace

import pytest
import torch
from torch import nn

from instrumentation.adapters import Qwen2ModelAdapter
from instrumentation.model_adapter import ComponentSite


class DummyBlock(nn.Module):
    """Minimal Qwen-shaped block for hook lifecycle tests."""

    def __init__(self) -> None:
        super().__init__()
        self.self_attn = nn.Linear(2, 2, bias=False)
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
