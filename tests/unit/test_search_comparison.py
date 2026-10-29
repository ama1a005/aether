"""Multi-seed comparison tests use synthetic evaluators only."""
from collections import Counter

import pytest

from discovery.budgeted import Candidate, Evaluation, SearchConfig
from discovery.comparison import aggregate_comparison, run_comparison
from discovery.rl.ppo import PPOConfig


def test_multi_seed_comparison_is_matched_and_reproducible():
    candidates = (Candidate("s", "sender"), Candidate("m", "message"),
                  Candidate("r", "receiver"), Candidate("n", "receiver"))
    factories = Counter()

    def factory(seed):
        factories[seed] += 1

        def evaluate(mask):
            required = {"s", "m", "r"}
            return Evaluation(float(required <= set(mask)), seed / 1000, 2,
                              {"seed": seed, "mask": mask})
        return evaluate

    config = SearchConfig(max_queries=16, faithfulness_threshold=.9,
                          max_benign_damage=.01, split="synthetic")
    ppo = PPOConfig(training_steps=8, rollout_steps=4, update_epochs=1, hidden_size=8)
    first = run_comparison(candidates, factory, config, [2, 1], ppo_template=ppo,
                           random_samples=4)
    second = run_comparison(candidates, factory, config, [1, 2], ppo_template=ppo,
                            random_samples=4)
    assert first == second
    assert factories == Counter({1: 10, 2: 10})
    assert len(first) == 10
    assert {(row.seed, row.method) for row in first} == {
        (seed, method) for seed in (1, 2) for method in
        ("greedy", "beam", "matched_random", "ppo", "ppo_frozen_policy")}
    summary = aggregate_comparison(first)
    assert all(value["n_seeds"] == 2 for value in summary.values())
    assert summary["greedy"]["feasible_rate"] == 1
    with pytest.raises(ValueError, match="unique"):
        run_comparison(candidates, factory, config, [1, 1], ppo_template=ppo)
