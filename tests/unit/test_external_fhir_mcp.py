"""Tests for the removable external FHIR MCP review layer."""

from __future__ import annotations

from copy import deepcopy

import pytest

from demo.backend.fhir_adapter import adapt_fhir_resources, attack_evidence
from demo.backend.fhir_service import fetch_case
from demo.backend.wso2_mcp_client import ExternalMCPError, MCPCallRecord, WSO2FHIRClient
from demo.fhir.fixtures import all_resources, case_registry, patient_id, resources_for_case
from demo.backend.repository import get_case


def _record(tool: str, arguments: dict, response: dict) -> MCPCallRecord:
    return MCPCallRecord(tool, arguments, response, 1.0, "0" * 64, {"name": "FHIR MCP Server", "version": "test"})


class FixtureMCPClient:
    """Protocol-shaped test double; production tests separately enforce fail-closed behavior."""

    def __init__(self, case_id: str) -> None:
        self.resources = resources_for_case(get_case(case_id))

    def read(self, resource_type: str, resource_id: str) -> MCPCallRecord:
        resource = next(item for item in self.resources if item["resourceType"] == resource_type and item["id"] == resource_id)
        return _record("read", {"type": resource_type, "id": resource_id}, resource)

    def search(self, resource_type: str, search_params: dict[str, str]) -> MCPCallRecord:
        matches = [item for item in self.resources if item["resourceType"] == resource_type]
        bundle = {"resourceType": "Bundle", "type": "searchset", "total": len(matches),
                  "entry": [{"resource": item} for item in matches]}
        return _record("search", {"type": resource_type, "searchParam": search_params}, bundle)


def test_fhir_fixtures_have_stable_ids_and_twelve_patients() -> None:
    first = all_resources()
    second = all_resources()
    patients = [item for item in first if item["resourceType"] == "Patient"]
    assert first == second
    assert len(patients) == 12
    assert patient_id("DEMO-PAT-001") == "aether-demo-pat-001"
    assert case_registry()["DEMO-PAT-012"] == "Patient/aether-demo-pat-012"
    assert all(item["meta"]["tag"][0]["code"] == "synthetic-review" for item in first)


def test_adapter_and_attack_keep_raw_fhir_immutable() -> None:
    raw = resources_for_case(get_case("DEMO-PAT-001"))
    preserved = deepcopy(raw)
    clean = adapt_fhir_resources(raw)
    attacked, delta = attack_evidence(clean)
    assert raw == preserved
    assert clean["risk_flag"] is True and attacked["risk_flag"] is False
    assert delta["path"] == "aether_evidence.risk_flag"
    assert {"patient_record", "vitals", "labs", "conditions", "medications", "diagnostic_reports"} <= set(clean["categories"])


@pytest.mark.parametrize("case_id", [f"DEMO-PAT-{number:03d}" for number in range(1, 13)])
def test_all_cases_fetch_through_client_boundary(case_id: str) -> None:
    result = fetch_case(case_id, FixtureMCPClient(case_id))
    assert result["evidence"]["source"] == "FHIR via WSO2 MCP"
    assert result["evidence"]["triage_recommendation"] == get_case(case_id).expected_action
    assert len(result["calls"]) == 7


def test_external_client_failure_has_no_direct_fhir_or_mock_fallback() -> None:
    client = WSO2FHIRClient("http://127.0.0.1:1/mcp")
    with pytest.raises(ExternalMCPError, match="external WSO2 MCP unavailable"):
        client.discover_tools()

