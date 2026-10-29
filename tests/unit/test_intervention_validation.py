"""Regression tests for silent intervention failures and SAE confounding."""
import pytest
import torch
from torch import nn

from causal.interventions.advanced import (
    InterventionTarget, execute_path_patch, residual_stream_patch,
    head_output_patch, sae_feature_patch,
)


@pytest.mark.parametrize("positions", [[], [-1], [True], [0, 0], [0.5]])
def test_direct_helpers_reject_invalid_token_selection(positions):
    with pytest.raises(ValueError):
        residual_stream_patch(torch.zeros(1, 2, 4), torch.ones(1, 2, 4), positions)


@pytest.mark.parametrize("heads", [0, -1, True, 1.5])
def test_direct_head_helper_rejects_invalid_head_count(heads):
    with pytest.raises(ValueError):
        head_output_patch(torch.zeros(1, 2, 4), torch.ones(1, 2, 4), [0], [0], heads)


def test_sae_self_patch_preserves_lossy_reconstruction_residual():
    class LossyCodec:
        def encode(self, tensor):
            return tensor * 0.5

        def decode(self, tensor):
            return tensor * 0.5

    destination = torch.tensor([[[4., 8.], [12., 16.]]])
    assert torch.equal(sae_feature_patch(destination, destination, [0], [0], LossyCodec()), destination)
    source = destination + 4
    patched = sae_feature_patch(destination, source, [0], [0], LossyCodec())
    assert torch.equal(patched, torch.tensor([[[5., 8.], [12., 16.]]]))


def test_unused_target_fails_and_removes_hook():
    class Branch(nn.Module):
        def __init__(self):
            super().__init__()
            self.unused = nn.Identity()

        def forward(self, x):
            return x

    model = Branch()
    x = torch.zeros(1, 2, 4)
    with pytest.raises(RuntimeError, match="did not execute"):
        execute_path_patch(model, x, [InterventionTarget("x", "unused", (0,), "clean")], {"x": x})
    assert not model.unused._forward_hooks
