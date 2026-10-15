"""Predeclared balanced-V2 internal-candidate classification rules."""

from __future__ import annotations

from typing import Literal

CandidateClass = Literal[
    "CASE_SPECIFIC",
    "LABEL_LEVEL",
    "GENERIC_OVERWRITE",
    "BROAD_CAUSAL_RESPONDER",
    "UNSUPPORTED",
    "INSUFFICIENT",
]

EFFECT_MINIMUM = 0.50
WEAK_EFFECT_MAXIMUM = 0.25
SEPARATION_MINIMUM = 0.20
EQUIVALENCE_TOLERANCE = 0.20


def classify_candidate(by_direction: dict[str, dict[str, float]]) -> CandidateClass:
    """Classify one candidate using both attack directions and semantic controls."""
    required_directions = {"A_TO_B", "B_TO_A"}
    required_metrics = {
        "paired_rescue", "paired_induction", "same_label_rescue",
        "opposite_label_rescue", "irrelevant_rescue", "matched_control_rescue",
    }
    if set(by_direction) != required_directions or any(
        not required_metrics.issubset(values) for values in by_direction.values()
    ):
        return "INSUFFICIENT"
    rows = list(by_direction.values())
    paired_ok = all(
        row["paired_rescue"] >= EFFECT_MINIMUM
        and row["paired_induction"] >= EFFECT_MINIMUM
        for row in rows
    )
    if all(
        abs(row["paired_rescue"]) <= WEAK_EFFECT_MAXIMUM
        and abs(row["paired_induction"]) <= WEAK_EFFECT_MAXIMUM
        for row in rows
    ):
        return "UNSUPPORTED"
    generic = all(
        min(row["paired_rescue"], row["same_label_rescue"], row["opposite_label_rescue"])
        >= EFFECT_MINIMUM
        and max(row["paired_rescue"], row["same_label_rescue"], row["opposite_label_rescue"])
        - min(row["paired_rescue"], row["same_label_rescue"], row["opposite_label_rescue"])
        <= EQUIVALENCE_TOLERANCE
        for row in rows
    )
    if generic:
        return "GENERIC_OVERWRITE"
    controls_ok = all(
        row["paired_rescue"] - row["irrelevant_rescue"] >= SEPARATION_MINIMUM
        and row["paired_rescue"] - row["matched_control_rescue"] >= SEPARATION_MINIMUM
        for row in rows
    )
    if paired_ok and controls_ok and all(
        row["paired_rescue"] - row["same_label_rescue"] >= SEPARATION_MINIMUM
        and row["paired_rescue"] - row["opposite_label_rescue"] >= SEPARATION_MINIMUM
        for row in rows
    ):
        return "CASE_SPECIFIC"
    if paired_ok and controls_ok and all(
        abs(row["paired_rescue"] - row["same_label_rescue"]) <= EQUIVALENCE_TOLERANCE
        and row["paired_rescue"] - row["opposite_label_rescue"] >= SEPARATION_MINIMUM
        for row in rows
    ):
        return "LABEL_LEVEL"
    return "BROAD_CAUSAL_RESPONDER"
