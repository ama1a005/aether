"""Prospective QCI-2 decision-semantic controls and support classification."""

from __future__ import annotations

import math
from statistics import median
from typing import Any, Iterable


def semantic_donor_mappings(rows: Iterable[dict[str, Any]]) -> dict[str, dict[str, str]]:
    """Return deterministic same- and opposite-decision donor maps.

    Attack direction fixes both the clean decision and the adversarial decision:
    A_TO_B cases have clean A / attacked B, while B_TO_A cases have clean B /
    attacked A. Cyclic donors within a direction therefore test semantic
    generalization. Index-aligned donors across directions test decision contrast.
    """
    groups: dict[str, list[str]] = {"A_TO_B": [], "B_TO_A": []}
    for row in rows:
        direction = str(row["direction"])
        if direction not in groups:
            raise ValueError(f"invalid attack direction: {direction}")
        groups[direction].append(str(row["case_id"]))
    for case_ids in groups.values():
        case_ids.sort()
    if not groups["A_TO_B"] or len(groups["A_TO_B"]) != len(groups["B_TO_A"]):
        raise ValueError("QCI-2 requires equal non-empty attack-direction groups")

    same: dict[str, str] = {}
    opposite: dict[str, str] = {}
    for direction, case_ids in groups.items():
        other = groups["B_TO_A" if direction == "A_TO_B" else "A_TO_B"]
        if len(case_ids) < 2:
            raise ValueError(f"QCI-2 requires two {direction} cases")
        for index, case_id in enumerate(case_ids):
            same[case_id] = case_ids[(index + 1) % len(case_ids)]
            opposite[case_id] = other[index]
    if any(case_id == donor for case_id, donor in same.items()):
        raise ValueError("QCI-2 same-decision mapping selected a self donor")
    return {"same_decision": same, "opposite_decision": opposite}


def _values(rows: list[dict[str, Any]], operator: str, expected_count: int) -> list[float]:
    """Extract one complete finite operator series from valid executions."""
    selected = [row for row in rows if row.get("operator") == operator]
    if len(selected) != expected_count:
        raise ValueError(f"QCI-2 requires {expected_count} {operator} executions")
    if any(row.get("status") != "ok" for row in selected):
        raise ValueError(f"QCI-2 {operator} contains failed executions")
    values = [float(row["normalized_effect"]) for row in selected]
    if any(not math.isfinite(value) for value in values):
        raise ValueError(f"QCI-2 {operator} contains non-finite effects")
    return values


def assess_semantic_candidate(
    rows: list[dict[str, Any]], thresholds: dict[str, Any], expected_count: int = 16
) -> dict[str, Any]:
    """Classify one candidate using decision generalization and contrast controls."""
    if not rows:
        raise ValueError("QCI-2 assessment has no executions")
    candidate_ids = {str(row["candidate_id"]) for row in rows}
    if len(candidate_ids) != 1:
        raise ValueError("QCI-2 assessment mixes candidates")
    operators = {
        "paired_rescue", "paired_induction",
        "same_decision_rescue", "same_decision_induction",
        "opposite_decision_rescue", "opposite_decision_induction",
        "irrelevant_position_rescue", "identity_clean_to_clean",
        "identity_attacked_to_attacked", "passive_hook",
    }
    observed = {str(row.get("operator")) for row in rows}
    if observed != operators:
        raise ValueError(f"QCI-2 operator set differs: {sorted(observed)}")
    counts = {name: sum(row.get("operator") == name for row in rows) for name in operators}
    if any(count != expected_count for count in counts.values()):
        raise ValueError(f"QCI-2 operator counts differ: {counts}")
    failures = [row for row in rows if row.get("status") != "ok"]
    if failures:
        return {
            "candidate_id": next(iter(candidate_ids)), "metrics": None,
            "checks": {"complete_valid_execution": False}, "status": "rejected",
            "reasons": ["execution_failure"], "failed_execution_count": len(failures),
        }

    series = {name: _values(rows, name, expected_count) for name in operators if not name.startswith(("identity_", "passive_"))}
    identity = [row for row in rows if str(row["operator"]).startswith("identity_")]
    passive = [row for row in rows if row["operator"] == "passive_hook"]
    controls_ok = all(bool(row.get("noninterference_pass")) for row in identity + passive)
    metrics = {
        "median_paired_rescue": median(series["paired_rescue"]),
        "median_paired_induction": median(series["paired_induction"]),
        "median_same_decision_rescue": median(series["same_decision_rescue"]),
        "median_same_decision_induction": median(series["same_decision_induction"]),
        "same_decision_rescue_gap": abs(median(series["paired_rescue"]) - median(series["same_decision_rescue"])),
        "same_decision_induction_gap": abs(median(series["paired_induction"]) - median(series["same_decision_induction"])),
        "rescue_opposite_contrast": median(series["paired_rescue"]) - median(series["opposite_decision_rescue"]),
        "induction_opposite_contrast": median(series["paired_induction"]) - median(series["opposite_decision_induction"]),
        "paired_minus_irrelevant_position": median(series["paired_rescue"]) - median(series["irrelevant_position_rescue"]),
        "paired_rescue_consistency": sum(v > 0.25 for v in series["paired_rescue"]) / expected_count,
        "paired_induction_consistency": sum(v > 0.25 for v in series["paired_induction"]) / expected_count,
        "same_rescue_consistency": sum(v > 0.25 for v in series["same_decision_rescue"]) / expected_count,
        "same_induction_consistency": sum(v > 0.25 for v in series["same_decision_induction"]) / expected_count,
        "controls_noninterfering": controls_ok,
    }
    checks = {
        "paired_rescue": metrics["median_paired_rescue"] >= thresholds["median_effect_min"],
        "paired_induction": metrics["median_paired_induction"] >= thresholds["median_effect_min"],
        "paired_rescue_consistency": metrics["paired_rescue_consistency"] >= thresholds["consistency_min"],
        "paired_induction_consistency": metrics["paired_induction_consistency"] >= thresholds["consistency_min"],
        "same_rescue_generalization": metrics["median_same_decision_rescue"] >= thresholds["median_effect_min"],
        "same_induction_generalization": metrics["median_same_decision_induction"] >= thresholds["median_effect_min"],
        "same_rescue_consistency": metrics["same_rescue_consistency"] >= thresholds["consistency_min"],
        "same_induction_consistency": metrics["same_induction_consistency"] >= thresholds["consistency_min"],
        "same_rescue_equivalence": metrics["same_decision_rescue_gap"] <= thresholds["same_decision_gap_max"],
        "same_induction_equivalence": metrics["same_decision_induction_gap"] <= thresholds["same_decision_gap_max"],
        "opposite_rescue_contrast": metrics["rescue_opposite_contrast"] >= thresholds["opposite_decision_contrast_min"],
        "opposite_induction_contrast": metrics["induction_opposite_contrast"] >= thresholds["opposite_decision_contrast_min"],
        "position_separation": metrics["paired_minus_irrelevant_position"] >= thresholds["position_contrast_min"],
        "control_noninterference": controls_ok,
    }
    return {
        "candidate_id": next(iter(candidate_ids)), "metrics": metrics, "checks": checks,
        "status": "supported" if all(checks.values()) else "rejected",
        "reasons": [name for name, passed in checks.items() if not passed],
    }
