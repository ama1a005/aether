"""Branching causal-control tests for staged mediator replay."""
import pytest
import torch
from torch import nn

from causal.interventions.advanced import InterventionTarget
from causal.interventions.path_replay import ReplaySite, replay_mediated_path, replay_path


class BranchingModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.source = nn.Identity()
        self.mediator = nn.Identity()
        self.bypass = nn.Identity()

    def forward(self, x):
        s = self.source(x)
        return self.mediator(2 * s) + self.bypass(10 * s)


def test_mediator_replay_excludes_competing_bypass():
    model = BranchingModel().eval()
    source = InterventionTarget("s", "source", (0,), "clean")
    mediator = InterventionTarget("m", "mediator", (0,), "propagated")
    bypass = InterventionTarget("b", "bypass", (0,), "baseline")
    result = replay_mediated_path(model, torch.zeros(1, 1, 1), source, mediator,
                                  torch.ones(1, 1, 1), (bypass,))
    assert result.baseline_output.item() == 0
    assert result.source_patched_output.item() == 2  # unrestricted source gives 12
    assert result.isolated_output.item() == 2
    assert result.propagated_mediator.item() == 2
    assert all(not module._forward_hooks for module in model.modules())


def test_reverse_path_is_rejected_and_hooks_cleaned():
    model = BranchingModel().eval()
    with pytest.raises(ValueError, match="before"):
        replay_mediated_path(model, torch.zeros(1, 1, 1),
                             InterventionTarget("m", "mediator", (0,), "clean"),
                             InterventionTarget("s", "source", (0,), "propagated"),
                             torch.ones(1, 1, 1), ())
    assert all(not module._forward_hooks for module in model.modules())


class RepeatedAndDeepModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.shared = nn.Identity()
        self.middle = nn.Identity()
        self.final = nn.Identity()
        self.bypass = nn.Identity()

    def forward(self, x):
        first = self.shared(x)
        second = self.shared(2 * first)
        middle = self.middle(3 * second)
        return self.final(5 * middle) + self.bypass(100 * first)


def test_repeated_calls_multiple_mediators_and_explicit_cut():
    model = RepeatedAndDeepModel().eval()
    source = ReplaySite(InterventionTarget("s", "shared", (0,), "clean"), call_index=1)
    middle = ReplaySite(InterventionTarget("m1", "middle", (0,), "propagated"))
    final = ReplaySite(InterventionTarget("m2", "final", (0,), "propagated"))
    bypass = ReplaySite(InterventionTarget("cut", "bypass", (0,), "baseline"))
    result = replay_path(model, torch.zeros(1, 1, 1), source, (middle, final),
                         torch.ones(1, 1, 1), (bypass,))
    assert [stage.activation.item() for stage in result.stages] == [3, 15]
    assert result.isolated_output.item() == 15
    assert result.execution_order[:2] == ("s@1", "m1@0")
    assert all(not module._forward_hooks for module in model.modules())


def test_missing_call_index_fails_and_cleans_hooks():
    model = RepeatedAndDeepModel().eval()
    source = ReplaySite(InterventionTarget("s", "shared", (0,), "clean"), call_index=2)
    mediator = ReplaySite(InterventionTarget("m", "middle", (0,), "propagated"))
    with pytest.raises(RuntimeError, match="did not execute"):
        replay_path(model, torch.zeros(1, 1, 1), source, (mediator,),
                    torch.ones(1, 1, 1))
    assert all(not module._forward_hooks for module in model.modules())
