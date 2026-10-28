"""Deterministic tensor-level tests for mandatory advanced interventions."""

import torch
from torch import nn
import pytest

from causal.interventions.advanced import (InterventionTarget, execute_path_patch,
                                           head_output_patch, intervention_hooks,
                                           residual_stream_patch, sae_feature_patch)


class IdentityCodec:
    """Exact codec used to isolate feature-selection mechanics."""

    def encode(self, activation: torch.Tensor) -> torch.Tensor:
        return activation

    def decode(self, features: torch.Tensor) -> torch.Tensor:
        return features


class TupleLayer(nn.Module):
    def forward(self, values):
        return values + 1, torch.tensor(9)


class TinyPath(nn.Module):
    def __init__(self):
        super().__init__()
        self.blocks = nn.ModuleList([nn.Identity(), TupleLayer()])

    def forward(self, values):
        values = self.blocks[0](values)
        values, auxiliary = self.blocks[1](values)
        return values, auxiliary


def test_residual_patch_changes_only_selected_tokens():
    destination = torch.zeros(1, 3, 4)
    source = torch.arange(12, dtype=torch.float32).reshape(1, 3, 4)
    patched = residual_stream_patch(destination, source, [1])
    assert torch.equal(patched[:, 1], source[:, 1])
    assert torch.equal(patched[:, [0, 2]], destination[:, [0, 2]])
    assert torch.equal(destination, torch.zeros_like(destination))


def test_head_patch_changes_cartesian_tokens_and_heads_only():
    destination = torch.zeros(1, 2, 8)
    source = torch.arange(16, dtype=torch.float32).reshape(1, 2, 8)
    patched = head_output_patch(destination, source, [0, 1], [1, 3], 4).reshape(1, 2, 4, 2)
    source_heads = source.reshape(1, 2, 4, 2)
    assert torch.equal(patched[:, :, [1, 3]], source_heads[:, :, [1, 3]])
    assert torch.equal(patched[:, :, [0, 2]], torch.zeros(1, 2, 2, 2))


def test_sae_feature_patch_changes_only_selected_latents_and_tokens():
    destination = torch.zeros(1, 2, 4)
    source = torch.ones(1, 2, 4)
    patched = sae_feature_patch(destination, source, [1], [0, 3], IdentityCodec())
    assert torch.equal(patched[0, 1], torch.tensor([1.0, 0.0, 0.0, 1.0]))
    assert torch.equal(patched[0, 0], destination[0, 0])


def test_path_patch_resolves_module_lists_preserves_tuples_and_logs_metadata():
    model = TinyPath()
    values = torch.zeros(1, 2, 4)
    sources = {"resid": torch.full_like(values, 3), "heads": torch.full_like(values, 7)}
    targets = (
        InterventionTarget("resid", "blocks.0", (0,), "clean-run"),
        InterventionTarget("heads", "blocks.1", (1,), "clean-run",
                           operator="head_output_patch", head_indices=(0,), num_heads=2),
    )
    output, records = execute_path_patch(model, values, targets, sources)
    assert torch.equal(output[0][0, 0], torch.full((4,), 4.0))
    assert torch.equal(output[0][0, 1, :2], torch.full((2,), 7.0))
    assert output[1].item() == 9
    assert [record.component_id for record in records] == ["resid", "heads"]
    assert all(record.source_run == "clean-run" for record in records)
    assert all(record.tensor_shape == (1, 2, 4) for record in records)
    assert not model.blocks[0]._forward_hooks and not model.blocks[1]._forward_hooks


def test_hooks_are_removed_when_model_forward_fails():
    model = TinyPath()
    target = InterventionTarget("x", "blocks.0", (5,), "clean")
    with pytest.raises(IndexError, match="token"):
        execute_path_patch(model, torch.zeros(1, 2, 4), [target], {"x": torch.zeros(1, 2, 4)})
    assert not model.blocks[0]._forward_hooks


@pytest.mark.parametrize("destination,source,error", [
    (torch.zeros(1, 2, 4), torch.zeros(1, 3, 4), "shapes"),
    (torch.zeros(1, 2, 4), torch.zeros(1, 2, 4, dtype=torch.float64), "dtype/device"),
])
def test_tensor_mismatch_fails_closed(destination, source, error):
    with pytest.raises(ValueError, match=error):
        residual_stream_patch(destination, source, [0])


def test_invalid_target_duplicate_path_and_missing_codec_fail_closed():
    with pytest.raises(ValueError, match="head indices"):
        InterventionTarget("x", "blocks.0", (0,), "clean", operator="head_output_patch",
                           num_heads=2)
    model = TinyPath()
    duplicate = InterventionTarget("x", "blocks.0", (0,), "clean")
    with pytest.raises(ValueError, match="component-unique"):
        with intervention_hooks(model, [duplicate, duplicate], {"x": torch.zeros(1, 2, 4)}):
            pass
    sae = InterventionTarget("sae", "blocks.0", (0,), "clean",
                             operator="sae_feature_patch", feature_indices=(0,))
    with pytest.raises(ValueError, match="Missing SAE codec"):
        execute_path_patch(model, torch.zeros(1, 2, 4), [sae], {"sae": torch.zeros(1, 2, 4)})
