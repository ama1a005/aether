"""Normal-CI tests for the removable review demo without model downloads."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from fastapi.testclient import TestClient

from demo.backend.app import app
from demo.backend.repository import ALLOWED_TOOLS, load_cases
from demo.backend.service import get_replay, run_pipeline, run_rescue
from demo.backend.tools import run_all_tools
from paired_trace.schemas import MediatorMessage


def test_all_12_case_schemas_ids_provenance_actions_and_tools() -> None:
    cases = load_cases()
    assert len(cases) == 12
    assert len({case.case_id for case in cases}) == 12
    assert all(case.dataset_origin == "aether_intermediate_review_demo" for case in cases)
    assert all(case.expected_action in {"ESCALATE", "DO_NOT_ESCALATE"} for case in cases)
    assert all(set(case.available_tools) <= ALLOWED_TOOLS for case in cases)
    assert all("validation" not in case.case_id.lower() and "test" not in case.case_id.lower() for case in cases)


def test_tool_execution_and_deterministic_serialization() -> None:
    case = load_cases()[0]
    rows = run_all_tools(case)
    assert [row.tool_name for row in rows] == case.available_tools
    assert all(row.execution_status == "COMPLETE" for row in rows)
    first = MediatorMessage.from_sender_code(case.case_id, "A", "evidence")
    second = MediatorMessage.from_sender_code(case.case_id, "A", "evidence")
    assert first.serialize() == second.serialize() and first.sha256() == second.sha256()


def test_clean_attack_and_rescue_are_integrated_with_core() -> None:
    clean = run_pipeline("DEMO-PAT-001", False)
    attack = run_pipeline("DEMO-PAT-001", True)
    rescue = run_rescue("DEMO-PAT-001", clean, attack)
    assert clean["receiver"]["decision"] == "ESCALATE"
    assert attack["receiver"]["decision"] == "DO_NOT_ESCALATE"
    assert attack["attack_delta"] == {"path":"ecg_analysis.recommendation_code","clean":"A","attacked":"B"}
    assert rescue["rescued_outcome"]["decision"] == "ESCALATE"
    assert rescue["normalized_recovery"] == 1.0
    assert "CrossAgentInterventionRunner" in rescue["source"]


def test_benign_and_non_ecg_representatives() -> None:
    assert run_pipeline("DEMO-PAT-002")["receiver"]["decision"] == "DO_NOT_ESCALATE"
    assert run_pipeline("DEMO-PAT-009")["receiver"]["decision"] == "ESCALATE"


def test_replay_artifacts_validate_and_keep_provenance() -> None:
    manifest = json.loads(Path("demo/cases/demo_case_manifest.json").read_text(encoding="utf-8"))
    assert manifest["case_count"] == 12 and manifest["validation_executions"] == 0
    for record in manifest["cases"]:
        replay = get_replay(record["case_id"])
        assert replay["provenance_type"] == "REPLAY — VERIFIED PRECOMPUTED EXECUTION"
        assert replay["content_sha256"] == record["artifact_id"]


def test_frontend_api_contracts() -> None:
    client = TestClient(app)
    assert client.get("/api/demo/health").json()["case_count"] == 12
    assert len(client.get("/api/demo/cases").json()) == 12
    clean = client.post("/api/demo/pipeline/clean", json={"case_id":"DEMO-PAT-001"})
    assert clean.status_code == 200 and clean.json()["provenance_type"] == "LIVE EXECUTION"
    assert client.get("/api/demo/evidence").status_code == 200
    assert client.get("/api/demo/system-status").status_code == 200
    model = client.get("/api/demo/model/status")
    assert model.status_code == 200 and model.json()["policy"].startswith("single instance")


def test_execution_modes_are_explicit_and_live_failure_does_not_fallback() -> None:
    client = TestClient(app)
    deterministic = client.post(
        "/api/demo/pipeline/clean",
        json={"case_id": "DEMO-PAT-001", "execution_mode": "deterministic"},
    )
    assert deterministic.status_code == 200
    assert deterministic.json()["execution_mode"] == "deterministic AETHER core demo pipeline"
    live = client.post(
        "/api/demo/pipeline/clean",
        json={"case_id": "DEMO-PAT-001", "execution_mode": "live_model_mcp"},
    )
    assert live.status_code == 503
    assert "live model + MCP execution failed" in live.json()["detail"]
    missing_live_replay = client.get("/api/demo/replay-live/DEMO-PAT-001")
    assert missing_live_replay.status_code == 404
    assert "qualification artifact does not exist" in missing_live_replay.json()["detail"]


def test_core_does_not_import_demo_and_removal_boundary_exists() -> None:
    for root in ("attacks","benchmarks","calibration","causal","contracts","discovery","experiments","instrumentation","paired_trace","remediation","target"):
        for path in Path(root).rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            imports = [node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))]
            assert not any((getattr(node,"module","") or "").startswith("demo") or any(alias.name.startswith("demo") for alias in getattr(node,"names",[])) for node in imports), path
    assert Path("docs/DEMO_REMOVAL.md").is_file()


def test_team_registry_guides_and_runbook_references_exist() -> None:
    ownership = Path("docs/team/team_ownership.yaml")
    runbook = Path("docs/INTERMEDIATE_REVIEW_RUNBOOK.md")
    assert ownership.is_file() and runbook.is_file()
    text = runbook.read_text(encoding="utf-8")
    assert "scripts/run_review_demo.ps1" in text and "DEMO-PAT-001" in text
