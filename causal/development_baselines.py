"""Development-only counterfactual baselines and accounting helpers."""

from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Sequence


@dataclass
class QueryBudget:
    """Explicit forward/generation query accounting."""

    sender_forwards: int = 0
    sender_generations: int = 0
    receiver_forwards: int = 0

    @property
    def total(self) -> int:
        """Return all model queries."""
        return self.sender_forwards + self.sender_generations + self.receiver_forwards


def deterministic_matched_controls(
    candidates: Sequence[str], excluded: Sequence[str], seeds: Sequence[int]
) -> list[str]:
    """Sample one stable control per seed without outcome-conditioned resampling."""
    pool = sorted(set(candidates) - set(excluded))
    if not pool:
        raise ValueError("no candidates remain for controls")
    return [pool[random.Random(seed).randrange(len(pool))] for seed in seeds]


def trace_level_replay(clean_message: str, attacked_message: str, use_clean: bool) -> str:
    """Replay a recorded mediator without inspecting internal activations."""
    return clean_message if use_clean else attacked_message


def clean_utility(before_codes: Sequence[str], after_codes: Sequence[str], before_scores: Sequence[float], after_scores: Sequence[float], invalid: int, latency_delta: float) -> dict[str, float | int]:
    """Measure clean behavior and cost for a candidate intervention."""
    if not (len(before_codes) == len(after_codes) == len(before_scores) == len(after_scores)):
        raise ValueError("clean utility arrays must align")
    n = len(before_codes)
    if n == 0:
        raise ValueError("clean utility requires examples")
    return {
        "N": n,
        "clean_accuracy_before": sum(code == "A" for code in before_codes) / n,
        "clean_accuracy_after": sum(code == "A" for code in after_codes) / n,
        "mean_logit_margin_change": sum(a - b for a, b in zip(after_scores, before_scores)) / n,
        "invalid_output_rate": invalid / n,
        "latency_change_seconds": latency_delta,
    }
