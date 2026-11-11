"""Tests for strict QCI-A1 evidence-bundle verification."""

from __future__ import annotations

import hashlib
import json

import pytest

from scripts.verify_qci_bundle import EXPECTED_OPERATORS
from scripts.verify_qci_audit_bundle import verify_audit


def _write(path, value) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def _audit_bundle(root) -> None:
    candidate = "sender.module.L22.mlp_output"
    rows = []
    for operator in EXPECTED_OPERATORS:
        for case in range(4):
            rows.append({
                "candidate_id": candidate,
                "case_id": str(case),
                "operator": operator,
                "status": "ok",
                "hook_cleanup": True,
                "intervention_applications": 0 if operator == "passive_hook" else 1,
            })
    (root / "raw_audit_interventions.jsonl").write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8"
    )
    _write(root / "candidate_audit_assessments.json", [{"candidate_id": candidate, "status": "supported"}])
    _write(root / "message_positive_controls.json", [{}] * 8)
    _write(root / "summary.json", {
        "run_id": "audit", "candidate_ids": [candidate],
        "audit_supported_candidates": [candidate], "candidate_execution_count": 28,
        "message_positive_control_count": 8, "development_audit_executions": 36,
        "validation_executions": 0, "test_executions": 0,
        "next_state": "READY_FOR_METHOD_FREEZE_REVIEW",
        "query_ledger": {"executions": 36, "maximum_executions": 240,
                         "forward_steps": 100, "maximum_forward_steps": 1200},
    })
    _write(root / "audit_preflight.json", {"decision": {"overall": "PASS"}})
    _write(root / "audit_model_access.json", {"state": "QCI_AUDIT_COMPLETE"})
    names = ["summary.json", "raw_audit_interventions.jsonl", "candidate_audit_assessments.json",
             "message_positive_controls.json", "audit_preflight.json", "audit_model_access.json"]
    hashes = {str(root / name): hashlib.sha256((root / name).read_bytes()).hexdigest() for name in names}
    _write(root / "manifest.json", {"artifact_paths": hashes})
    archive = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in names + ["manifest.json"]}
    _write(root / "archive_contents.json", archive)


def test_qci_audit_verifier_accepts_complete_bundle(tmp_path) -> None:
    _audit_bundle(tmp_path)
    report = verify_audit(tmp_path)
    assert report["overall"] == "PASS"
    assert report["candidate_execution_count"] == 28
    assert report["next_gate"] == "READY_FOR_METHOD_FREEZE_REVIEW"


def test_qci_audit_verifier_rejects_locked_split_access(tmp_path) -> None:
    _audit_bundle(tmp_path)
    summary = json.loads((tmp_path / "summary.json").read_text())
    summary["validation_executions"] = 1
    _write(tmp_path / "summary.json", summary)
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    key = next(key for key in manifest["artifact_paths"] if key.endswith("summary.json"))
    manifest["artifact_paths"][key] = hashlib.sha256((tmp_path / "summary.json").read_bytes()).hexdigest()
    _write(tmp_path / "manifest.json", manifest)
    archive = json.loads((tmp_path / "archive_contents.json").read_text())
    archive["summary.json"] = hashlib.sha256((tmp_path / "summary.json").read_bytes()).hexdigest()
    archive["manifest.json"] = hashlib.sha256((tmp_path / "manifest.json").read_bytes()).hexdigest()
    _write(tmp_path / "archive_contents.json", archive)
    with pytest.raises(ValueError, match="locked split"):
        verify_audit(tmp_path)
