"""Build deterministic, synthetic FHIR R4 review resources."""

from __future__ import annotations

from typing import Any

from demo.backend.repository import load_cases

SYNTHETIC_TAG = {"system": "https://aether.invalid/fhir/tags", "code": "synthetic-review"}


def patient_id(case_id: str) -> str:
    """Return the stable FHIR logical Patient id for an AETHER case."""
    return "aether-" + case_id.lower()


def case_registry() -> dict[str, str]:
    """Map every review case to its stable FHIR Patient reference."""
    return {case.case_id: f"Patient/{patient_id(case.case_id)}" for case in load_cases()}


def _meta() -> dict[str, Any]:
    return {"tag": [SYNTHETIC_TAG]}


def _observation(pid: str, suffix: str, display: str, value: Any, unit: str | None = None) -> dict[str, Any]:
    resource: dict[str, Any] = {
        "resourceType": "Observation", "id": f"{pid}-{suffix}", "meta": _meta(),
        "status": "final", "subject": {"reference": f"Patient/{pid}"},
        "code": {"coding": [{"system": "https://aether.invalid/fhir/codes", "code": suffix, "display": display}]},
        "effectiveDateTime": "2026-10-19T09:00:00Z",
    }
    if isinstance(value, bool):
        resource["valueBoolean"] = value
    elif isinstance(value, (int, float)):
        resource["valueQuantity"] = {"value": value, **({"unit": unit} if unit else {})}
    else:
        resource["valueString"] = str(value)
    return resource


def resources_for_case(case: Any) -> list[dict[str, Any]]:
    """Convert one demo case to a compact set of valid-looking synthetic FHIR R4 resources."""
    pid = patient_id(case.case_id)
    family, *given = case.display_name.split()[::-1]
    resources: list[dict[str, Any]] = [{
        "resourceType": "Patient", "id": pid, "meta": _meta(), "active": True,
        "identifier": [{"system": "https://aether.invalid/demo-case-id", "value": case.case_id}],
        "name": [{"use": "official", "family": family, "given": list(reversed(given))}],
        "gender": {"M": "male", "F": "female"}.get(case.sex, "other"),
        "birthDate": f"{2026 - case.age}-01-01",
    }, {
        "resourceType": "Encounter", "id": f"{pid}-encounter", "meta": _meta(), "status": "finished",
        "class": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "AMB"},
        "subject": {"reference": f"Patient/{pid}"},
        "reasonCode": [{"text": case.presenting_complaint}],
    }]
    for key, value in case.vitals.items():
        resources.append(_observation(pid, f"vital-{key.replace('_', '-')}", key.replace("_", " ").title(), value))
    for key, value in case.labs.items():
        resources.append(_observation(pid, f"lab-{key.replace('_', '-')}", key.replace("_", " ").title(), value))
    resources.append(_observation(pid, "risk-flag", "Synthetic review urgency flag", case.expected_action == "ESCALATE"))
    resources.append({
        "resourceType": "DiagnosticReport", "id": f"{pid}-ecg", "meta": _meta(), "status": "final",
        "code": {"text": "Synthetic electrocardiogram interpretation"},
        "subject": {"reference": f"Patient/{pid}"}, "conclusion": case.ecg.get("summary", "Not indicated"),
    })
    for index, condition in enumerate(case.history):
        resources.append({"resourceType": "Condition", "id": f"{pid}-condition-{index + 1}", "meta": _meta(),
                          "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]},
                          "code": {"text": condition}, "subject": {"reference": f"Patient/{pid}"}})
    for index, medication in enumerate(case.medications):
        resources.append({"resourceType": "MedicationRequest", "id": f"{pid}-medication-{index + 1}", "meta": _meta(),
                          "status": "active", "intent": "order", "medicationCodeableConcept": {"text": medication},
                          "subject": {"reference": f"Patient/{pid}"}})
    for index, allergy in enumerate(case.allergies):
        resources.append({"resourceType": "AllergyIntolerance", "id": f"{pid}-allergy-{index + 1}", "meta": _meta(),
                          "patient": {"reference": f"Patient/{pid}"}, "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical", "code": "active"}]},
                          "code": {"text": allergy}})
    return resources


def all_resources() -> list[dict[str, Any]]:
    """Return resources for all twelve cases in stable order."""
    return [resource for case in load_cases() for resource in resources_for_case(case)]

