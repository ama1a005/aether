"""Primary review pipeline: external FHIR MCP with deterministic AETHER agents."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
import json
from time import perf_counter
from typing import Any
from uuid import uuid4

from causal.bridge.intervention import CrossAgentInterventionRunner
from demo.backend.fhir_adapter import adapt_fhir_resources, attack_evidence
from demo.backend.service import _git_commit, _save_run
from demo.backend.wso2_mcp_client import MCPCallRecord, WSO2FHIRClient
from demo.fhir.fixtures import patient_id
from paired_trace.metrics import LABEL_TO_DECISION, mediation_recovery
from paired_trace.schemas import MediatorMessage

RESOURCE_TYPES = ("Observation", "Condition", "MedicationRequest", "AllergyIntolerance", "Encounter", "DiagnosticReport")


def _bundle_resources(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict) and payload.get("resourceType") == "Bundle":
        return [entry["resource"] for entry in payload.get("entry", []) if isinstance(entry.get("resource"), dict)]
    if isinstance(payload, dict) and payload.get("resourceType"):
        return [payload]
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict) and item.get("resourceType")]
    return []


def fetch_case(case_id: str, client: WSO2FHIRClient | None = None) -> dict[str, Any]:
    """Fetch a case exclusively through WSO2 MCP; there is deliberately no REST fallback."""
    client = client or WSO2FHIRClient()
    calls: list[MCPCallRecord] = [client.read("Patient", patient_id(case_id))]
    for resource_type in RESOURCE_TYPES:
        calls.append(client.search(resource_type, {"patient": patient_id(case_id)}))
    resources = [resource for call in calls for resource in _bundle_resources(call.response)]
    if not any(resource.get("resourceType") == "Patient" for resource in resources):
        raise ValueError(f"MCP did not return Patient for {case_id}")
    return {"resources": resources, "calls": [asdict(call) for call in calls], "evidence": adapt_fhir_resources(resources)}


def run_fhir_pipeline(case_id: str, attacked: bool = False, client: WSO2FHIRClient | None = None) -> dict[str, Any]:
    """Run external MCP retrieval, explicit evidence adaptation, and deterministic A/B agents."""
    started = perf_counter()
    fetched = fetch_case(case_id, client)
    clean_evidence = fetched["evidence"]
    selected, delta = attack_evidence(clean_evidence) if attacked else (clean_evidence, None)
    code = "A" if selected["risk_flag"] else "B"
    mediator = MediatorMessage.from_sender_code(case_id, code, "deterministic rule over AETHER risk_flag")
    decision = LABEL_TO_DECISION[code]
    run_id = f"demo_fhir_{case_id.lower()}_{'attack' if attacked else 'clean'}_{uuid4().hex[:8]}"
    result = {
        "run_id": run_id, "case_id": case_id, "condition": "attacked" if attacked else "clean",
        "provenance_type": "REAL WSO2 FHIR MCP + DETERMINISTIC AGENTS", "execution_mode": "real_fhir_mcp_deterministic",
        "mcp_server": "WSO2 FHIR MCP Server", "transport": "Streamable HTTP",
        "raw_fhir_mcp_data": fetched["resources"], "mcp_calls": fetched["calls"],
        "clean_evidence": clean_evidence, "attacked_evidence": selected if attacked else None, "attack_delta": delta,
        "sender": {"source": "deterministic AETHER evidence rule", "raw_output": code},
        "mediator": {"raw": mediator.serialize(), "parsed": asdict(mediator), "sha256": mediator.sha256()},
        "receiver": {"source": "paired_trace.metrics.LABEL_TO_DECISION", "raw_output": code,
                     "decision": decision, "score": 1.0 if code == "A" else -1.0,
                     "received_mediator_sha256": mediator.sha256()},
        "runtime_seconds": perf_counter() - started, "utc_timestamp": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git_commit(), "validation_executions": 0, "test_executions": 0,
    }
    _save_run(result)
    return result


def run_fhir_rescue(case_id: str) -> dict[str, Any]:
    """Patch the clean mediator into the attacked trajectory."""
    clean = run_fhir_pipeline(case_id, False)
    attacked = run_fhir_pipeline(case_id, True)
    runner = CrossAgentInterventionRunner(None, None, attacked["mediator"]["parsed"],
                                          lambda message: 1.0 if message["decision_code"] == "A" else -1.0, None)
    before, after = runner.run_message_patch(attacked["mediator"]["parsed"], clean["mediator"]["parsed"])
    return {"case_id": case_id, "provenance_type": "REAL WSO2 FHIR MCP + DETERMINISTIC AGENTS",
            "intervention": "whole_clean_message_substitution", "score_before": before, "score_after": after,
            "normalized_recovery": mediation_recovery(clean["receiver"]["score"], attacked["receiver"]["score"], after),
            "rescued_outcome": {"decision": clean["receiver"]["decision"], "score": after},
            "clean_mediator": clean["mediator"], "attacked_outcome": attacked["receiver"],
            "utc_timestamp": datetime.now(timezone.utc).isoformat(), "git_commit": _git_commit()}

