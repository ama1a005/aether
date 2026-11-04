"""Predeclared paired security/causal statistics with explicit denominators."""
from __future__ import annotations

from dataclasses import dataclass
from math import comb, isfinite
from statistics import fmean, pstdev
from typing import Sequence

from attacks.stats import bootstrap_ci


@dataclass(frozen=True)
class OutcomeRecord:
    """One case/seed/method outcome; errors remain eligible denominator rows."""
    case_id: str
    seed: int
    method: str
    family: str
    eligible: bool
    clean_correct: bool
    attack_success: bool
    valid: bool
    error_type: str | None = None
    faithfulness: float | None = None
    benign_damage: float | None = None
    forward_passes: int = 0

    def __post_init__(self) -> None:
        if not self.case_id or not self.method or not self.family or self.seed < 0:
            raise ValueError("Outcome identity and seed are required")
        if self.valid == (self.error_type is not None):
            raise ValueError("Invalid outcomes require an error_type and valid outcomes forbid one")
        for value in (self.faithfulness, self.benign_damage):
            if value is not None and not isfinite(value):
                raise ValueError("Optional outcome metrics must be finite")
        if self.benign_damage is not None and self.benign_damage < 0:
            raise ValueError("Benign damage cannot be negative")
        if type(self.forward_passes) is not int or self.forward_passes < 0:
            raise ValueError("Forward passes must be a nonnegative integer")
        if not self.eligible and self.attack_success:
            raise ValueError("Ineligible attempts cannot count as attack successes")


def _exact_mcnemar(left: Sequence[bool], right: Sequence[bool]) -> dict[str, float | int]:
    if len(left) != len(right):
        raise ValueError("Paired arrays must align")
    left_only = sum(a and not b for a, b in zip(left, right))
    right_only = sum(b and not a for a, b in zip(left, right))
    discordant = left_only + right_only
    if discordant == 0:
        p_value = 1.0
    else:
        tail = sum(comb(discordant, k) for k in range(min(left_only, right_only) + 1)) / 2 ** discordant
        p_value = min(1.0, 2 * tail)
    return {"left_only": left_only, "right_only": right_only,
            "discordant": discordant, "exact_p_value": p_value}


def summarize_outcomes(records: Sequence[OutcomeRecord], *, bootstrap_seed: int = 0,
                       bootstrap_samples: int = 2000) -> dict[str, object]:
    """Summarize ASR, conditional ASR, errors, costs and seed stability."""
    if not records:
        raise ValueError("Outcome records are required")
    keys = [(row.case_id, row.seed, row.method) for row in records]
    if len(set(keys)) != len(keys):
        raise ValueError("Outcome case/seed/method rows must be unique")
    result: dict[str, object] = {}
    for method in sorted({row.method for row in records}):
        group = [row for row in records if row.method == method]
        eligible = [row for row in group if row.eligible]
        conditional = [row for row in eligible if row.clean_correct]
        successes = sum(row.attack_success for row in eligible)
        ci = bootstrap_ci(successes, len(eligible), n_bootstrap=bootstrap_samples,
                          seed=bootstrap_seed) if eligible else (0.0, 0.0)
        by_seed = []
        for seed in sorted({row.seed for row in eligible}):
            seed_rows = [row for row in eligible if row.seed == seed]
            by_seed.append(sum(row.attack_success for row in seed_rows) / len(seed_rows))
        valid_faithfulness = [row.faithfulness for row in group
                              if row.valid and row.faithfulness is not None]
        valid_damage = [row.benign_damage for row in group
                        if row.valid and row.benign_damage is not None]
        result[method] = {
            "attempts": len(group), "eligible": len(eligible), "successes": successes,
            "asr": successes / len(eligible) if eligible else None,
            "asr_ci_lower": ci[0], "asr_ci_upper": ci[1],
            "conditional_eligible": len(conditional),
            "conditional_asr": (sum(row.attack_success for row in conditional) / len(conditional)
                                if conditional else None),
            "invalid_or_error": sum(not row.valid for row in group),
            "forward_passes": sum(row.forward_passes for row in group),
            "faithfulness_mean": fmean(valid_faithfulness) if valid_faithfulness else None,
            "benign_damage_mean": fmean(valid_damage) if valid_damage else None,
            "seed_asr_mean": fmean(by_seed) if by_seed else None,
            "seed_asr_std": pstdev(by_seed) if by_seed else None,
            "seed_count": len(by_seed),
        }
    return result


def paired_method_comparison(records: Sequence[OutcomeRecord], left_method: str,
                             right_method: str) -> dict[str, object]:
    """Compare aligned eligible case/seed pairs without dropping invalid rows."""
    by_method = {method: {(row.case_id, row.seed): row for row in records if row.method == method}
                 for method in (left_method, right_method)}
    if set(by_method[left_method]) != set(by_method[right_method]):
        raise ValueError("Methods do not contain identical case/seed pairs")
    pairs = sorted(by_method[left_method])
    left = [by_method[left_method][key] for key in pairs]
    right = [by_method[right_method][key] for key in pairs]
    if any(a.eligible != b.eligible for a, b in zip(left, right)):
        raise ValueError("Paired eligibility decisions differ")
    eligible = [(a, b) for a, b in zip(left, right) if a.eligible]
    test = _exact_mcnemar([a.attack_success for a, _ in eligible],
                          [b.attack_success for _, b in eligible])
    return {"left_method": left_method, "right_method": right_method,
            "paired_rows": len(pairs), "eligible_pairs": len(eligible), **test}
