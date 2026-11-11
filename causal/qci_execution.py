"""Frozen QCI-1.1 intervention accounting and support classification."""

from __future__ import annotations

from dataclasses import dataclass
import math
import re
from statistics import median
from typing import Any, Iterable


@dataclass(frozen=True)
class QCICandidate:
    """One selected Qwen module or pre-projection attention head."""

    candidate_id: str
    agent: str
    family: str
    layer: int
    component_type: str | None = None
    head: int | None = None


@dataclass
class QueryLedger:
    """Fail-closed execution and model-forward budget ledger."""

    maximum_executions: int
    maximum_forward_steps: int
    executions: int = 0
    forward_steps: int = 0

    def charge(self, *, executions: int = 1, forward_steps: int = 1) -> None:
        """Charge work before execution and reject budget overruns."""
        if executions < 0 or forward_steps < 0:
            raise ValueError("QCI budget charges must be non-negative")
        if self.executions + executions > self.maximum_executions:
            raise RuntimeError("QCI intervention-execution budget exhausted")
        if self.forward_steps + forward_steps > self.maximum_forward_steps:
            raise RuntimeError("QCI model-forward budget exhausted")
        self.executions += executions
        self.forward_steps += forward_steps


def parse_candidate(row: dict[str, Any]) -> QCICandidate:
    """Parse a frozen selection row into an exact intervention target."""
    identifier, agent, family = str(row["candidate_id"]), str(row["agent"]), str(row["family"])
    if agent not in {"sender", "receiver"}:
        raise ValueError(f"invalid QCI agent: {agent}")
    if family == "module":
        match = re.fullmatch(r"module\.L(\d+)\.(attention_output|mlp_output)", identifier)
        if not match:
            raise ValueError(f"invalid QCI module candidate: {identifier}")
        return QCICandidate(identifier, agent, family, int(match.group(1)), match.group(2))
    if family == "head":
        match = re.fullmatch(r"head\.L(\d+)\.H(\d+)\.pre_o_proj", identifier)
        if not match:
            raise ValueError(f"invalid QCI head candidate: {identifier}")
        return QCICandidate(identifier, agent, family, int(match.group(1)), head=int(match.group(2)))
    raise ValueError(f"invalid QCI family: {family}")


def shuffled_donor_mapping(rows: Iterable[dict[str, Any]]) -> dict[str, str]:
    """Map every case to the next case cyclically within attack direction."""
    groups: dict[str, list[str]] = {"A_TO_B": [], "B_TO_A": []}
    for row in rows:
        direction = str(row["direction"])
        if direction not in groups:
            raise ValueError(f"invalid attack direction: {direction}")
        groups[direction].append(str(row["case_id"]))
    mapping: dict[str, str] = {}
    for direction, case_ids in groups.items():
        case_ids.sort()
        if len(case_ids) < 2:
            raise ValueError(f"QCI shuffled controls require two {direction} cases")
        for index, case_id in enumerate(case_ids):
            mapping[case_id] = case_ids[(index + 1) % len(case_ids)]
    if any(case_id == donor for case_id, donor in mapping.items()):
        raise ValueError("QCI shuffled control selected a self donor")
    return mapping


def rescue_effect(clean: float, attacked: float, intervened: float) -> float:
    """Return unclipped attacked-to-clean normalized recovery."""
    denominator = clean - attacked
    if abs(denominator) < 1e-6:
        raise ValueError("QCI rescue denominator is degenerate")
    value = (intervened - attacked) / denominator
    if not math.isfinite(value):
        raise ValueError("QCI rescue effect is non-finite")
    return value


def induction_effect(clean: float, attacked: float, intervened: float) -> float:
    """Return unclipped clean-to-attacked normalized induction."""
    denominator = clean - attacked
    if abs(denominator) < 1e-6:
        raise ValueError("QCI induction denominator is degenerate")
    value = (clean - intervened) / denominator
    if not math.isfinite(value):
        raise ValueError("QCI induction effect is non-finite")
    return value


def _values(rows: list[dict[str, Any]], operator: str) -> list[float]:
    selected = [row for row in rows if row.get("operator") == operator]
    if len(selected) != 16:
        raise ValueError(f"QCI candidate requires 16 {operator} executions")
    if any(row.get("status") != "ok" for row in selected):
        raise ValueError(f"QCI {operator} contains failed executions")
    values = [float(row["normalized_effect"]) for row in selected]
    if any(not math.isfinite(value) for value in values):
        raise ValueError(f"QCI {operator} contains non-finite effects")
    return values


def assess_candidate(
    rows: list[dict[str, Any]], thresholds: dict[str, Any]
) -> dict[str, Any]:
    """Apply the immutable QCI discovery support criteria to one candidate."""
    if not rows:
        raise ValueError("QCI assessment has no executions")
    candidate_ids = {str(row["candidate_id"]) for row in rows}
    if len(candidate_ids) != 1:
        raise ValueError("QCI assessment mixes candidates")
    expected_operators = {
        "paired_rescue", "paired_induction", "shuffled_donor_rescue",
        "irrelevant_position_rescue", "identity_clean_to_clean",
        "identity_attacked_to_attacked", "passive_hook",
    }
    observed = {str(row.get("operator")) for row in rows}
    if observed != expected_operators:
        raise ValueError(f"QCI operator set differs: {sorted(observed)}")
    counts = {operator: sum(row.get("operator") == operator for row in rows) for operator in expected_operators}
    if any(count != 16 for count in counts.values()):
        raise ValueError(f"QCI operator counts differ: {counts}")
    failures = [row for row in rows if row.get("status") != "ok"]
    if failures:
        return {
            "candidate_id": next(iter(candidate_ids)),
            "metrics": None,
            "checks": {"complete_valid_execution": False},
            "status": "rejected",
            "reasons": ["execution_failure"],
            "failed_execution_count": len(failures),
        }
    rescue = _values(rows, "paired_rescue")
    induction = _values(rows, "paired_induction")
    shuffled = _values(rows, "shuffled_donor_rescue")
    irrelevant = _values(rows, "irrelevant_position_rescue")
    identity_rows = [row for row in rows if str(row["operator"]).startswith("identity_")]
    passive_rows = [row for row in rows if row["operator"] == "passive_hook"]
    controls_noninterfering = all(
        row.get("status") == "ok" and bool(row.get("noninterference_pass"))
        for row in identity_rows + passive_rows
    ) and len(identity_rows) == 32 and len(passive_rows) == 16
    metrics = {
        "median_rescue": median(rescue),
        "rescue_above_0_25_fraction": sum(value > 0.25 for value in rescue) / 16,
        "median_induction": median(induction),
        "induction_above_0_25_fraction": sum(value > 0.25 for value in induction) / 16,
        "paired_minus_shuffled_median": median(rescue) - median(shuffled),
        "paired_minus_irrelevant_position": median(rescue) - median(irrelevant),
        "all_raw_effects_expected_direction": all(value >= 0.0 for value in rescue + induction),
        "controls_noninterfering": controls_noninterfering,
    }
    checks = {
        "median_rescue": metrics["median_rescue"] >= thresholds["median_rescue_min"],
        "rescue_consistency": metrics["rescue_above_0_25_fraction"] >= thresholds["rescue_above_0_25_fraction_min"],
        "median_induction": metrics["median_induction"] >= thresholds["median_induction_min"],
        "induction_consistency": metrics["induction_above_0_25_fraction"] >= thresholds["induction_above_0_25_fraction_min"],
        "shuffled_separation": metrics["paired_minus_shuffled_median"] >= thresholds["paired_minus_shuffled_median_min"],
        "position_separation": metrics["paired_minus_irrelevant_position"] >= thresholds["paired_minus_irrelevant_position_min"],
        "raw_direction": metrics["all_raw_effects_expected_direction"] is bool(thresholds["all_raw_effects_expected_direction"]),
        "control_noninterference": controls_noninterfering,
    }
    return {
        "candidate_id": next(iter(candidate_ids)),
        "metrics": metrics,
        "checks": checks,
        "status": "supported" if all(checks.values()) else "rejected",
        "reasons": [name for name, passed in checks.items() if not passed],
    }
