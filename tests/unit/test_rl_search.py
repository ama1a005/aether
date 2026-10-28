"""RL tests use a declared synthetic evaluator and are not research evidence."""

import pytest
import torch

from discovery.budgeted import Candidate, Evaluation, SearchConfig
from discovery.rl.ppo import (CausalPruningEnv, PPOConfig, RewardWeights, ppo_search,
                              ppo_search_with_trace)


CANDIDATES = tuple(Candidate(identifier, region) for identifier, region in (
    ("S", "sender"), ("SN", "sender"), ("M", "message"),
    ("MN", "message"), ("R", "receiver"), ("RN", "receiver")))


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
    assert reward > 0 and breakdown.size < 0 and not done
    assert len(env.cache) == 2
    env.reset()
    env.step(noise)
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
