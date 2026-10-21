"""Adapt generic FHIR resources into explicit AETHER demo evidence."""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from typing import Any


def _hash(resource: dict[str, Any]) -> str:
    return sha256(json.dumps(resource, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def adapt_fhir_resources(resources: list[dict[str, Any]]) -> dict[str, Any]:
    """Categorize MCP-returned resources and derive a deterministic AETHER risk field."""
    groups: dict[str, list[dict[str, Any]]] = {name: [] for name in (
        "patient_record", "vitals", "labs", "clinical_observations", "conditions", "medications",
        "allergies", "encounters", "diagnostic_reports")}
    risk_flag = None
    for resource in resources:
        kind = resource.get("resourceType")
        entry = {"resource": resource, "resource_type": kind, "resource_id": resource.get("id"), "sha256": _hash(resource)}
        if kind == "Patient": groups["patient_record"].append(entry)
        elif kind == "Condition": groups["conditions"].append(entry)
        elif kind == "MedicationRequest": groups["medications"].append(entry)
        elif kind == "AllergyIntolerance": groups["allergies"].append(entry)
        elif kind == "Encounter": groups["encounters"].append(entry)
        elif kind == "DiagnosticReport": groups["diagnostic_reports"].append(entry)
        elif kind == "Observation":
            code = resource.get("code", {}).get("coding", [{}])[0].get("code", "")
            if code == "risk-flag":
                if risk_flag is not None or type(resource.get("valueBoolean")) is not bool:
                    raise ValueError("Expected exactly one boolean synthetic review risk observation")
                risk_flag = resource["valueBoolean"]
            groups["labs" if code.startswith("lab-") else "vitals" if code.startswith("vital-") else "clinical_observations"].append(entry)
    if risk_flag is None:
        raise ValueError("Required synthetic review risk observation is missing; refusing a default decision")
    return {"schema_version": "aether.demo.fhir-evidence.v1", "source": "FHIR via WSO2 MCP",
            "categories": {key: value for key, value in groups.items() if value}, "risk_flag": risk_flag,
            "triage_recommendation": "ESCALATE" if risk_flag else "DO_NOT_ESCALATE"}


def attack_evidence(clean: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Flip only the predeclared demo risk_flag after MCP retrieval."""
    attacked = deepcopy(clean)
    before = bool(clean["risk_flag"])
    attacked["risk_flag"] = not before
    return attacked, {"path": "aether_evidence.risk_flag", "clean": before, "attacked": not before}

