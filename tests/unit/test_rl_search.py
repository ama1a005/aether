"""RL tests use a declared synthetic evaluator and are not research evidence."""

import pytest
import torch
import numpy as np

from discovery.budgeted import Candidate, Evaluation, SearchConfig
from discovery.rl.ppo import (CausalPruningEnv, PPOConfig, RewardWeights, ppo_search,
                              ppo_search_with_trace)


CANDIDATES = tuple(Candidate(identifier, region) for identifier, region in (
    ("S", "sender"), ("SN", "sender"), ("M", "message"),
    ("MN", "message"), ("R", "receiver"), ("RN", "receiver")))


@pytest.mark.parametrize("terminated,expected_return", [(False, 2.8), (True, 1.0)])
def test_gae_bootstraps_rollout_cutoff_but_not_terminal(monkeypatch, terminated, expected_return):
    from discovery.rl.ppo import _ActorCritic, _update
    model = _ActorCritic(1, 2, 2)
    with torch.no_grad():
        for parameter in model.parameters():
            parameter.zero_()
    observed_errors = []
    original_square = torch.square

    def capture_value_error(value):
        observed_errors.append(value.detach().clone())
        return original_square(value)

    monkeypatch.setattr(torch, "square", capture_value_error)
    transitions = [(np.zeros(1, dtype=np.float32), np.ones(2, dtype=bool),
                    0, -np.log(2), 0.0, terminated, 1.0)]
    _update(model, torch.optim.Adam(model.parameters()), transitions,
            PPOConfig(gamma=0.9, update_epochs=1), bootstrap_value=2.0)
    assert observed_errors[0].item() == pytest.approx(-expected_return)


def evaluator(mask: tuple[str, ...]) -> Evaluation:
    required = {"S", "M", "R"}
    faithfulness = 1.0 if required <= set(mask) else 0.0
    return Evaluation(faithfulness, 0.0, 4, {"retained": list(mask), "required": sorted(required)})


def test_environment_has_typed_removals_stop_and_global_query_ledger():
    env = CausalPruningEnv(CANDIDATES, evaluator, SearchConfig(max_queries=8, split="synthetic"),
                           RewardWeights())
    assert len(env.observation()) == len(CANDIDATES) + 6
    assert env.action_mask().tolist() == [True] * 7
    noise = next(index for index, item in enumerate(env.ids) if item == "MN")
    _, reward, done, breakdown = env.step(noise)
    assert reward > 0 and breakdown.size > 0 and not done
    assert len(env.cache) == 2
    env.reset()
    _, _, _, cached_breakdown = env.step(noise)
    assert cached_breakdown.cost == 0.0
    assert breakdown.cost == pytest.approx(-0.004)
    assert breakdown.total == pytest.approx(sum((breakdown.effect, breakdown.benign,
                                                 breakdown.size, breakdown.cost,
                                                 breakdown.feasible_stop)))
    assert len(env.cache) == 2  # repeated episode uses measured cache
    _, stop_reward, done, stopped = env.step(env.stop_action)
    assert done and stop_reward == stopped.feasible_stop > 0


def test_environment_rejects_removed_invalid_and_post_terminal_actions():
    env = CausalPruningEnv(CANDIDATES, evaluator, SearchConfig(split="synthetic"), RewardWeights())
    action = next(index for index, item in enumerate(env.ids) if item == "SN")
    env.step(action)
    with pytest.raises(ValueError, match="masked"):
        env.step(action)
    env.step(env.stop_action)
    with pytest.raises(RuntimeError, match="terminated"):
        env.step(env.stop_action)


def test_ppo_is_seeded_budgeted_and_recovers_best_observed_path():
    search = SearchConfig(max_queries=32, faithfulness_threshold=0.99,
                          max_benign_damage=0.0, split="synthetic")
    ppo = PPOConfig(seed=7, training_steps=128, rollout_steps=32, update_epochs=2)
    first = ppo_search(CANDIDATES, evaluator, search, ppo)
    second = ppo_search(CANDIDATES, evaluator, search, ppo)
    assert first.retained == second.retained == ("M", "R", "S")
    assert first.queries == second.queries <= search.max_queries
    assert first.forward_passes == first.queries * 4
    assert [record.retained for record in first.records] == [record.retained for record in second.records]
    assert all(record.evaluation.raw_outputs for record in first.records)


def test_ppo_does_not_mutate_caller_torch_rng_state():
    state = torch.random.get_rng_state().clone()
    ppo_search(CANDIDATES, evaluator, SearchConfig(max_queries=8, split="synthetic"),
               PPOConfig(seed=3, training_steps=8, rollout_steps=4, update_epochs=1))
    assert torch.equal(torch.random.get_rng_state(), state)


def test_ppo_retains_complete_auditable_training_trace():
    config = PPOConfig(seed=4, training_steps=12, rollout_steps=4, update_epochs=1)
    outcome = ppo_search_with_trace(CANDIDATES, evaluator,
                                    SearchConfig(max_queries=12, split="synthetic"), config)
    assert len(outcome.training_trace) == config.training_steps
    assert {record.action.split(":")[0] for record in outcome.training_trace} <= {"remove", "stop"}
    assert all(len(record.action_mask) == len(CANDIDATES) + 1 for record in outcome.training_trace)
    assert all(record.reward.total == pytest.approx(record.reward.total)
               for record in outcome.training_trace)


def test_configuration_and_evaluator_fail_closed():
    with pytest.raises(ValueError):
        PPOConfig(training_steps=0)
    with pytest.raises(ValueError):
        RewardWeights(effect=-1)
    with pytest.raises(TypeError, match="Evaluation"):
        CausalPruningEnv(CANDIDATES, lambda _: None,
                         SearchConfig(split="synthetic"), RewardWeights())


def test_budget_masks_unseen_actions_but_preserves_stop():
    env = CausalPruningEnv(CANDIDATES, evaluator, SearchConfig(max_queries=1, split="synthetic"),
                           RewardWeights())
    assert not env.action_mask()[:-1].any()
    assert env.action_mask()[-1]
