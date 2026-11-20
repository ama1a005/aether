"""Typed demo-only contracts; frozen research contracts remain untouched."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal


Action = Literal["ESCALATE", "DO_NOT_ESCALATE"]


@dataclass(frozen=True)
class DemoPatientCase:
    """One versioned, source-attributed review demonstration case."""

    case_id: str
    display_name: str
    age: int
    sex: str
    presenting_complaint: str
    symptom_duration: str
    vitals: dict[str, Any]
    history: list[str]
    medications: list[str]
    allergies: list[str]
    ecg: dict[str, Any]
    labs: dict[str, Any]
    additional_assessments: dict[str, Any]
    timeline: list[str]
    available_tools: list[str]
    expected_action: Action
    primary_attack_target: str
    notes: str
    provenance: dict[str, Any]
    schema_version: str = "aether.demo.case.v1"
    dataset_origin: str = "ptbxl_v1.0.3_physionet"

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible case."""
        return asdict(self)


@dataclass(frozen=True)
class ToolExecution:
    """One deterministic tool execution over a source-attributed demo case."""

    tool_name: str
    request: dict[str, Any]
    response: dict[str, Any]
    execution_status: str
    elapsed_ms: float
    provenance: str = "PTB-XL-DERIVED DEMONSTRATION"
