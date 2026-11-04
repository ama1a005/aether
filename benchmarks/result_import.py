"""Strict importers for official benchmark outputs and standardized summaries."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class BenchmarkResult:
    """One benchmark case retained with validity and error provenance."""

    benchmark: str
    case_id: str
    success: bool | None
    valid: bool
    error_type: str | None = None

    def __post_init__(self) -> None:
        if not self.benchmark or not self.case_id:
            raise ValueError("Benchmark and case ID are required")
        if self.valid != (self.error_type is None):
            raise ValueError("Valid rows cannot have errors and invalid rows must have one")
        if not self.valid and self.success is not None:
            raise ValueError("Invalid rows cannot claim success or failure")


def _load_rows(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload if isinstance(payload, list) else payload.get("results")
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"No result rows found in {path}")
    if not all(isinstance(row, dict) for row in rows):
        raise ValueError("Every result row must be an object")
    return rows


def import_official_results(path: Path, *, benchmark: str, id_field: str,
                            success_field: str, error_field: str = "error") -> list[BenchmarkResult]:
    """Import explicit official rows without treating errors as missing cases."""
    imported: list[BenchmarkResult] = []
    seen: set[str] = set()
    for row in _load_rows(path):
        case_id = str(row.get(id_field, ""))
        if not case_id or case_id in seen:
            raise ValueError(f"Missing or duplicate case ID: {case_id!r}")
        seen.add(case_id)
        error = row.get(error_field)
        if error is not None:
            imported.append(BenchmarkResult(benchmark, case_id, None, False, str(error)))
        else:
            success = row.get(success_field)
            if not isinstance(success, bool):
                raise ValueError(f"Case {case_id} lacks a boolean {success_field}")
            imported.append(BenchmarkResult(benchmark, case_id, success, True))
    return imported


def write_summary(rows: Iterable[BenchmarkResult], output: Path) -> dict[str, Any]:
    """Write counts with invalid cases retained in the total denominator."""
    values = list(rows)
    if not values:
        raise ValueError("At least one result is required")
    valid = sum(row.valid for row in values)
    successes = sum(row.success is True for row in values)
    summary = {"schema_version": 1, "benchmark": values[0].benchmark,
               "total": len(values), "valid": valid, "invalid": len(values) - valid,
               "successes": successes, "success_rate_total": successes / len(values),
               "rows": [asdict(row) for row in values]}
    output.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return summary
