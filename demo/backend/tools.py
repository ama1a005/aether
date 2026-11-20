"""Deterministic MCP-style tools backed only by the selected demo fixture."""

from __future__ import annotations

from time import perf_counter
from typing import Any, Callable

from demo.backend.schemas import DemoPatientCase, ToolExecution
from target.mcp.tools import get_patient_history, get_vital_signs


def _code(case: DemoPatientCase) -> str:
    return "A" if case.expected_action == "ESCALATE" else "B"


def _patient_record(case: DemoPatientCase) -> dict[str, Any]:
    features = {"prior_diagnoses": case.history, "medication_count": len(case.medications), "comorbidities": case.history}
    return {**get_patient_history(case.case_id, features), "source_data_available": False,
            "recommendation_code": _code(case)}


def _ecg_analysis(case: DemoPatientCase) -> dict[str, Any]:
    return {**case.ecg, "recommendation_code": _code(case),
            "risk_level": "CRITICAL" if case.expected_action == "ESCALATE" else "LOW",
            "risk_level_derivation": "AETHER demonstration mapping from published diagnostic superclasses",
            "flags": case.ecg["diagnostic_superclasses"]}


def _vitals(case: DemoPatientCase) -> dict[str, Any]:
    if not case.vitals:
        return {"values": {}, "source_data_available": False,
                "recommendation_code": _code(case)}
    return {**get_vital_signs(case.case_id, case.vitals), "source_data_available": True,
            "recommendation_code": _code(case)}


def _labs(case: DemoPatientCase) -> dict[str, Any]:
    return {"values": case.labs, "source_data_available": bool(case.labs),
            "recommendation_code": _code(case)}


def _medication(case: DemoPatientCase) -> dict[str, Any]:
    return {"medications": case.medications, "source_data_available": bool(case.medications),
            "recommendation_code": _code(case)}


def _allergy(case: DemoPatientCase) -> dict[str, Any]:
    return {"allergies": case.allergies, "source_data_available": bool(case.allergies),
            "recommendation_code": _code(case)}


def _neuro(case: DemoPatientCase) -> dict[str, Any]:
    return {"screen": case.additional_assessments.get("neuro_screen"),
            "source_data_available": "neuro_screen" in case.additional_assessments,
            "recommendation_code": _code(case)}


def _risk(case: DemoPatientCase) -> dict[str, Any]:
    return {"risk_score": case.additional_assessments.get("risk_score"),
            "source_data_available": "risk_score" in case.additional_assessments,
            "recommendation_code": _code(case)}


TOOLS: dict[str, Callable[[DemoPatientCase], dict[str, Any]]] = {
    "patient_record": _patient_record, "ecg_analysis": _ecg_analysis, "lab_results": _labs,
    "vitals_monitor": _vitals, "medication_safety": _medication, "allergy_check": _allergy,
    "neuro_assessment": _neuro, "risk_assessment": _risk,
}


def run_tool(case: DemoPatientCase, tool_name: str) -> ToolExecution:
    """Execute one registered tool and retain exact request/response provenance."""
    if tool_name not in case.available_tools or tool_name not in TOOLS:
        raise ValueError(f"tool {tool_name} is unavailable for {case.case_id}")
    started = perf_counter()
    request = {
        "case_id": case.case_id,
        "dataset_origin": case.dataset_origin,
        "source_record_id": case.provenance["source_record_id"],
        "source_fold": case.provenance["source_fold"],
    }
    response = TOOLS[tool_name](case)
    return ToolExecution(tool_name, request, response, "COMPLETE", (perf_counter() - started) * 1000)


def run_all_tools(case: DemoPatientCase) -> list[ToolExecution]:
    """Execute every declared tool in stable fixture order."""
    return [run_tool(case, name) for name in case.available_tools]
