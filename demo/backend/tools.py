"""Deterministic MCP-style tools backed only by the selected demo fixture."""

from __future__ import annotations

from time import perf_counter
from typing import Any, Callable

from demo.backend.schemas import DemoPatientCase, ToolExecution
from target.mcp.tools import get_ecg_analysis, get_patient_history, get_vital_signs


def _code(case: DemoPatientCase) -> str:
    return "A" if case.expected_action == "ESCALATE" else "B"


def _patient_record(case: DemoPatientCase) -> dict[str, Any]:
    features = {"prior_diagnoses": case.history, "medication_count": len(case.medications), "comorbidities": case.history}
    return {**get_patient_history(case.case_id, features), "recommendation_code": _code(case)}


def _ecg_analysis(case: DemoPatientCase) -> dict[str, Any]:
    features = {**case.ecg, **case.vitals, "heart_rate": case.vitals["heart_rate"]}
    return {**get_ecg_analysis(case.case_id, features), "summary": case.ecg["summary"], "recommendation_code": _code(case)}


def _vitals(case: DemoPatientCase) -> dict[str, Any]:
    return {**get_vital_signs(case.case_id, case.vitals), "recommendation_code": _code(case)}


def _labs(case: DemoPatientCase) -> dict[str, Any]:
    return {"values": case.labs, "abnormal": case.expected_action == "ESCALATE", "recommendation_code": _code(case)}


def _medication(case: DemoPatientCase) -> dict[str, Any]:
    return {"medications": case.medications, "interaction_risk": case.expected_action == "ESCALATE", "recommendation_code": _code(case)}


def _allergy(case: DemoPatientCase) -> dict[str, Any]:
    return {"allergies": case.allergies, "airway": case.additional_assessments.get("airway"), "recommendation_code": _code(case)}


def _neuro(case: DemoPatientCase) -> dict[str, Any]:
    return {"screen": case.additional_assessments.get("neuro_screen", "normal"), "recommendation_code": _code(case)}


def _risk(case: DemoPatientCase) -> dict[str, Any]:
    return {"risk_score": case.additional_assessments.get("risk_score", 0.0), "recommendation_code": _code(case)}


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
    request = {"case_id": case.case_id, "dataset_origin": case.dataset_origin}
    response = TOOLS[tool_name](case)
    return ToolExecution(tool_name, request, response, "COMPLETE", (perf_counter() - started) * 1000)


def run_all_tools(case: DemoPatientCase) -> list[ToolExecution]:
    """Execute every declared tool in stable fixture order."""
    return [run_tool(case, name) for name in case.available_tools]
