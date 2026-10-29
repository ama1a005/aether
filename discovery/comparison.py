"""Matched multi-seed search comparisons without hidden evaluator reuse."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite
from statistics import fmean, pstdev
from typing import Callable, Sequence

from discovery.budgeted import Candidate, Evaluation, SearchConfig, random_control, search
from discovery.rl.policy import evaluate_policy
from discovery.rl.ppo import PPOConfig, RewardWeights, ppo_search_with_trace

EvaluatorFactory = Callable[[int], Callable[[tuple[str, ...]], Evaluation]]


@dataclass(frozen=True)
class ComparisonRow:
    """One method/seed result with measured cost and terminal metrics."""
    seed: int
    method: str
    retained: tuple[str, ...]
    feasible: bool
    faithfulness: float
    benign_damage: float
    queries: int
    forward_passes: int


def run_comparison(candidates: Sequence[Candidate], evaluator_factory: EvaluatorFactory,
                   search_config: SearchConfig, seeds: Sequence[int], *,
                   ppo_template: PPOConfig = PPOConfig(),
                   rewards: RewardWeights = RewardWeights(),
                   random_samples: int = 32) -> tuple[ComparisonRow, ...]:
    """Run greedy, beam, random, PPO search and frozen PPO policy per seed.

    Each method receives a fresh evaluator instance. The random control is
    region/size matched to that seed's greedy result. Seed order is normalized.
    """
    normalized = tuple(sorted(seeds))
    if not normalized or len(set(normalized)) != len(normalized) or any(
            type(seed) is not int or seed < 0 for seed in normalized):
        raise ValueError("Seeds must be unique nonnegative integers")
    if type(random_samples) is not int or random_samples < 1:
        raise ValueError("random_samples must be positive")
    rows: list[ComparisonRow] = []

    def append(seed: int, result) -> None:
        rows.append(ComparisonRow(seed, result.method, result.retained, result.feasible,
                                  result.evaluation.faithfulness,
                                  result.evaluation.benign_damage,
                                  result.queries, result.forward_passes))

    for seed in normalized:
        greedy = search(candidates, evaluator_factory(seed), search_config, method="greedy")
        append(seed, greedy)
        append(seed, search(candidates, evaluator_factory(seed), search_config, method="beam"))
        append(seed, random_control(candidates, evaluator_factory(seed), search_config,
                                    greedy.retained, samples=random_samples, seed=seed))
        ppo_config = PPOConfig(**{**asdict(ppo_template), "seed": seed})
        trained = ppo_search_with_trace(candidates, evaluator_factory(seed), search_config,
                                        ppo_config, rewards)
        append(seed, trained.result)
        append(seed, evaluate_policy(trained.policy, candidates, evaluator_factory(seed),
                                     search_config))
    return tuple(rows)


def aggregate_comparison(rows: Sequence[ComparisonRow]) -> dict[str, dict[str, float | int]]:
    """Aggregate per-seed outcomes while retaining rows as primary evidence."""
    if not rows:
        raise ValueError("Comparison rows are required")
    result: dict[str, dict[str, float | int]] = {}
    for method in sorted({row.method for row in rows}):
        group = [row for row in rows if row.method == method]
        metrics = ("faithfulness", "benign_damage", "queries", "forward_passes")
        summary: dict[str, float | int] = {
            "n_seeds": len(group), "feasible_count": sum(row.feasible for row in group),
            "feasible_rate": fmean(float(row.feasible) for row in group),
        }
        for metric in metrics:
            values = [float(getattr(row, metric)) for row in group]
            summary[f"{metric}_mean"] = fmean(values)
            summary[f"{metric}_std"] = pstdev(values)
        if any(isinstance(value, float) and not isfinite(value) for value in summary.values()):
            raise RuntimeError("Comparison aggregation produced nonfinite output")
        result[method] = summary
    return result
