"""Checkpoint and inference tests; synthetic results are not model evidence."""

from copy import deepcopy

import pytest
import torch

from discovery.budgeted import Candidate, Evaluation, SearchConfig
from discovery.rl.ppo import PPOConfig, ppo_search_with_trace
from discovery.rl.policy import evaluate_policy, load_policy, save_policy


def test_checkpoint_roundtrip_and_fresh_evaluation(tmp_path, monkeypatch):
    candidates = (Candidate("x", "sender"), Candidate("y", "receiver"))
    calls = []

    def evaluate(mask):
        calls.append(mask)
        return Evaluation(float("x" in mask), 0, 1, {"mask": mask})

    config = SearchConfig(max_queries=3, split="synthetic")
    outcome = ppo_search_with_trace(candidates, evaluate, config,
                                   PPOConfig(training_steps=8, rollout_steps=4))
    path = tmp_path / "policy.json"
    rng = torch.get_rng_state().clone()
    save_policy(outcome.policy, path)
    loaded = load_policy(path)
    assert torch.equal(rng, torch.get_rng_state())
    assert loaded == outcome.policy

    def forbidden(*args, **kwargs):
        raise AssertionError("Inference must not construct an optimizer")

    monkeypatch.setattr(torch.optim, "Adam", forbidden)
    calls.clear()
    first = evaluate_policy(loaded, candidates, evaluate, config)
    assert calls[0] == ("x", "y")
    assert len(calls) == first.queries <= 3
    second = evaluate_policy(loaded, candidates, evaluate, config)
    assert first == second
    assert loaded == outcome.policy
    with pytest.raises(ValueError, match="identities"):
        evaluate_policy(loaded, (Candidate("z", "sender"),), evaluate, config)
    bad = deepcopy(loaded)
    bad["state_dict"]["policy.bias"][0] = float("nan")
    with pytest.raises(ValueError, match="nonfinite"):
        save_policy(bad, path)


def test_policy_reports_terminal_failure_not_best_visited():
    candidates = (Candidate("x", "sender"),)
    config = SearchConfig(max_queries=2, split="synthetic")

    def evaluate(mask):
        return Evaluation(float(bool(mask)), 0, 1, {"mask": mask})

    policy = ppo_search_with_trace(candidates, evaluate, config,
                                  PPOConfig(training_steps=1)).policy
    # Force removal even though the initial full mask is feasible.
    policy["state_dict"]["policy.weight"] = [[0.0] * 64, [0.0] * 64]
    policy["state_dict"]["policy.bias"] = [10.0, 0.0]
    result = evaluate_policy(policy, candidates, evaluate, config)
    assert result.retained == ()
    assert not result.feasible
    assert result.records[0].evaluation.faithfulness == 1.0
