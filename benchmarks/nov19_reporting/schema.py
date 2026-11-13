"""Typed contracts and serialization for external benchmark handoffs."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "aether.nov19.external_benchmark.v1"


@dataclass(frozen=True)
class ExternalBenchmarkHandoff:
    """Standardized external benchmark summary handoff contract."""
    benchmark: str  # "BFCL" | "MCPTox" | "TAMAS"
    evidence_class: str
    upstream_revision: str
    model_revision: str
    cohort: list[str] | str
    selection_rule: str
    official_evaluator_executed: bool
    status: str  # "PASSED" | "FAILED" | "BLOCKED" | "NOT_EXECUTED"
    denominators: dict[str, int]
    raw_artifacts: list[str]
    artifact_sha256: dict[str, str]
    limitations: list[str]
    metrics: dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError(f"Unsupported schema version: {self.schema_version}")
        if self.benchmark not in {"BFCL", "MCPTox", "TAMAS"}:
            raise ValueError(f"Unknown benchmark: {self.benchmark}")
        if self.status not in {"PASSED", "FAILED", "BLOCKED", "NOT_EXECUTED", "SMOKE_PASSED"}:
            raise ValueError(f"Invalid status: {self.status}")
        required_denom = {"eligible", "invalid", "errors"}
        if not required_denom.issubset(self.denominators):
            missing = required_denom - set(self.denominators)
            raise ValueError(f"Missing required denominator fields: {missing}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def write_json(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
