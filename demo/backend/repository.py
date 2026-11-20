"""Load and validate isolated demo fixtures."""

from __future__ import annotations

import json
from pathlib import Path

from demo.backend.schemas import DemoPatientCase

CASE_PATH = Path(__file__).parents[1] / "cases" / "ptbxl_demo_cases.json"
ALLOWED_TOOLS = frozenset({
    "patient_record", "ecg_analysis", "lab_results", "vitals_monitor",
    "medication_safety", "allergy_check", "neuro_assessment", "risk_assessment",
})


def load_cases(path: Path = CASE_PATH) -> list[DemoPatientCase]:
    """Load exactly 12 validated PTB-XL-derived demonstration cases."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = [DemoPatientCase(**item) for item in payload["cases"]]
    ids = [case.case_id for case in cases]
    if len(cases) != 12 or len(set(ids)) != 12:
        raise ValueError("demo registry must contain exactly 12 unique cases")
    if ids != [f"DEMO-PAT-{index:03d}" for index in range(1, 13)]:
        raise ValueError("demo case IDs must be the fixed DEMO-PAT-001..012 sequence")
    for case in cases:
        if case.dataset_origin != "ptbxl_v1.0.3_physionet":
            raise ValueError("PTB-XL v1.0.3 provenance is required")
        provenance = case.provenance
        if (
            provenance.get("source_record_id") is None
            or provenance.get("source_fold") not in range(1, 9)
            or provenance.get("license") != "CC BY 4.0"
            or provenance.get("action_is_aether_derived") is not True
        ):
            raise ValueError(f"incomplete or unsafe provenance for {case.case_id}")
        if case.expected_action not in {"ESCALATE", "DO_NOT_ESCALATE"}:
            raise ValueError("invalid expected action")
        if not case.available_tools or not set(case.available_tools) <= ALLOWED_TOOLS:
            raise ValueError(f"invalid tools for {case.case_id}")
        if "validation" in case.case_id.lower() or "test" in case.case_id.lower():
            raise ValueError("scientific split identifiers are forbidden in demo fixtures")
    return cases


def get_case(case_id: str) -> DemoPatientCase:
    """Return one case or raise a clear lookup error."""
    for case in load_cases():
        if case.case_id == case_id:
            return case
    raise KeyError(f"unknown demo case: {case_id}")
