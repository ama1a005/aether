"""Tests for the evidence-backed Phase-1 completion audit."""

from __future__ import annotations

import json

import yaml

from scripts.audit_phase1_completion import audit


def test_repository_completion_audit_reports_known_evidence_and_open_gates() -> None:
    report = audit()
    statuses = {row["id"]: row["status"] for row in report["gates"]}
    assert report["overall"] == "INCOMPLETE"
    assert statuses["qwen_qualification"] == "PASS"
    assert statuses["qwen_instrumentation_acceptance"] == "PASS"
    assert statuses["qwen_development_capture"] == "PASS"
    assert statuses["qci_discovery_interventions"] == "MISSING"
    assert statuses["qci_development_audit"] == "BLOCKED"
    assert statuses["tracr_known_structure_intervention"] == "FAIL"
    assert statuses["ioi_causal_calibration"] == "PASS"


def test_completion_audit_rejects_missing_predicate(tmp_path) -> None:
    (tmp_path / "evidence.json").write_text(json.dumps({"overall": "PASS"}), encoding="utf-8")
    config = {
        "schema_version": "aether.phase1-completion.v1",
        "claim_boundary": "test",
        "gates": [{
            "id": "gate", "category": "test", "kind": "json",
            "path": "evidence.json", "expect": {"test_executions": 0},
        }],
    }
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    report = audit(tmp_path, config_path)
    assert report["overall"] == "INCOMPLETE"
    assert report["gates"][0]["status"] == "FAIL"
    assert "missing predicate" in report["gates"][0]["reasons"][0]
