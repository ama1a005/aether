"""Select all feasible non-dominated repairs from comparable validation evidence.

This is a pure selector over executed measurements, not an experiment runner or
permission to open a held-out split. It never manufactures missing measurements.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from numbers import Real
from typing import Sequence


def _number(name: str, value: float, *, probability: bool = False) -> None:
    if isinstance(value, bool) or not isinstance(value, Real) or not isfinite(value) or value < 0:
        raise ValueError(f"{name} must be a finite nonnegative number")
    if probability and value > 1:
        raise ValueError(f"{name} must be in [0, 1]")


@dataclass(frozen=True)
class RepairMeasurement:
    """Measured security, utility and cost for one validation repair candidate."""

    id: str
    region: str
    source_run_id: str
    split: str
    cohort_sha256: str
    baseline_asr: float
    asr: float
    benign_utility: float
    failure_rate: float
    latency_ms: float
    extra_forward_passes: int
    modified_components: int
    modified_message_units: int

    def __post_init__(self) -> None:
        if not self.id or not self.source_run_id:
            raise ValueError("Candidate id and source run provenance are required")
        if self.region not in {"sender", "message", "receiver", "none"}:
            raise ValueError("Unknown repair region")
        if self.split != "validation":
            raise ValueError("Repair selection requires validation measurements, never test measurements")
        if len(self.cohort_sha256) != 64 or any(c not in "0123456789abcdef" for c in self.cohort_sha256):
            raise ValueError("A SHA-256 identifying the exact paired evaluation cohort is required")
        for name in ("baseline_asr", "asr", "benign_utility", "failure_rate"):
            _number(name, getattr(self, name), probability=True)
        _number("latency_ms", self.latency_ms)
        for name in ("extra_forward_passes", "modified_components", "modified_message_units"):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} must be a nonnegative integer")

    def objectives(self) -> tuple[float, ...]:
        """Return separately reported objectives, all oriented toward minimization."""
        return (self.asr, -self.benign_utility, self.failure_rate, self.latency_ms,
                self.extra_forward_passes, self.modified_components, self.modified_message_units)


@dataclass(frozen=True)
class RepairConstraints:
    """Prospectively declared feasibility limits for validation selection."""

    max_asr: float
    min_benign_utility: float
    max_failure_rate: float
    max_latency_ms: float | None = None

    def __post_init__(self) -> None:
        for name in ("max_asr", "min_benign_utility", "max_failure_rate"):
            _number(name, getattr(self, name), probability=True)
        if self.max_latency_ms is not None:
            _number("max_latency_ms", self.max_latency_ms)


@dataclass(frozen=True)
class FrontierResult:
    """Entire eligible frontier, dominated ids, and explicit exclusion reasons."""

    frontier: tuple[RepairMeasurement, ...]
    dominated: tuple[str, ...]
    excluded: dict[str, tuple[str, ...]]


def select_frontier(measurements: Sequence[RepairMeasurement], constraints: RepairConstraints) -> FrontierResult:
    """Keep every feasible Pareto-optimal repair, including exact objective ties."""
    if len({row.id for row in measurements}) != len(measurements):
        raise ValueError("Candidate ids must be unique")
    cohorts = {(row.cohort_sha256, row.baseline_asr) for row in measurements}
    if len(cohorts) > 1:
        raise ValueError("Cannot compare different cohorts or no-defense baselines")
    eligible = []
    excluded = {}
    for row in sorted(measurements, key=lambda row: row.id):
        reasons = []
        if row.asr > constraints.max_asr:
            reasons.append("security_threshold")
        if row.benign_utility < constraints.min_benign_utility:
            reasons.append("benign_utility_floor")
        if row.failure_rate > constraints.max_failure_rate:
            reasons.append("failure_rate_limit")
        if constraints.max_latency_ms is not None and row.latency_ms > constraints.max_latency_ms:
            reasons.append("latency_limit")
        if reasons:
            excluded[row.id] = tuple(reasons)
        else:
            eligible.append(row)
    frontier = []
    dominated = []
    for row in eligible:
        target = row.objectives()
        if any(all(a <= b for a, b in zip(other.objectives(), target))
               and any(a < b for a, b in zip(other.objectives(), target)) for other in eligible):
            dominated.append(row.id)
        else:
            frontier.append(row)
    return FrontierResult(tuple(frontier), tuple(dominated), excluded)
