"""Adapters from executed case interventions to shared search evaluations."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite
from statistics import fmean
from typing import Callable, Mapping, Sequence

from causal.metrics.faithfulness import compute_faithfulness
from discovery.budgeted import Evaluation


@dataclass(frozen=True)
class CaseMeasurement:
    """Raw executed scores for one case and one retained intervention mask."""
    case_id: str
    delta_full: float
    delta_circuit: float
    clean_score_before: float
    clean_score_after: float
    forward_passes: int
    raw_outputs: Mapping[str, object]

    def __post_init__(self) -> None:
        values = (self.delta_full, self.delta_circuit,
                  self.clean_score_before, self.clean_score_after)
        if not self.case_id or any(not isfinite(value) for value in values):
            raise ValueError("Case measurement identities and scores must be finite")
        if type(self.forward_passes) is not int or self.forward_passes < 1:
            raise ValueError("Case measurement requires positive forward-pass accounting")
        if not self.raw_outputs:
            raise ValueError("Case measurement raw outputs are required")


class MeasuredMaskEvaluator:
    """Aggregate a fixed case cohort without inspecting labels or dropping errors."""

    def __init__(self, case_ids: Sequence[str],
                 execute: Callable[[str, tuple[str, ...]], CaseMeasurement],
                 *, fixed_retained: Sequence[str] = ()) -> None:
        self.case_ids = tuple(case_ids)
        if (not self.case_ids or len(set(self.case_ids)) != len(self.case_ids)
                or any(not case_id for case_id in self.case_ids)):
            raise ValueError("Evaluator case IDs must be nonempty and unique")
        self.execute = execute
        self.fixed_retained = tuple(sorted(fixed_retained))
        if len(set(self.fixed_retained)) != len(self.fixed_retained):
            raise ValueError("Fixed retained component IDs must be unique")

    def __call__(self, retained: tuple[str, ...]) -> Evaluation:
        """Execute every declared case and return mean metrics plus all raw rows."""
        if len(set(retained)) != len(retained):
            raise ValueError("Retained component IDs must be unique")
        effective = tuple(sorted((*retained, *self.fixed_retained)))
        if len(set(effective)) != len(effective):
            raise ValueError("Action and fixed component scopes overlap")
        rows = []
        for case_id in self.case_ids:
            row = self.execute(case_id, effective)
            if not isinstance(row, CaseMeasurement) or row.case_id != case_id:
                raise ValueError("Executor returned the wrong case measurement")
            rows.append(row)
        faithfulness = [compute_faithfulness(row.delta_full, row.delta_circuit) for row in rows]
        benign = [abs(row.clean_score_after - row.clean_score_before) for row in rows]
        raw = {"requested_retained": list(retained), "fixed_retained": list(self.fixed_retained),
               "effective_retained": list(effective),
               "cases": [{**asdict(row), "faithfulness": score,
                          "benign_damage": damage}
                         for row, score, damage in zip(rows, faithfulness, benign)]}
        return Evaluation(fmean(faithfulness), fmean(benign),
                          sum(row.forward_passes for row in rows), raw)
