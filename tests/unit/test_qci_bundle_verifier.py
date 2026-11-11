"""Tests for strict downloaded QCI bundle verification."""

from __future__ import annotations

import hashlib
import json

import pytest

from scripts.verify_qci_bundle import EXPECTED_OPERATORS, verify


def _write_json(path, value) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def _bundle(tmp_path):
    rows = []
    candidates = [f"{'sender' if index < 6 else 'receiver'}.node{index}" for index in range(12)]
    for candidate in candidates:
        for operator in sorted(EXPECTED_OPERATORS):
            for case in range(16):
                rows.append({
                    "candidate_id": candidate, "case_id": str(case), "operator": operator,
                    "status": "ok", "hook_cleanup": True,
                    "intervention_applications": 0 if operator == "passive_hook" else 1,
                })
    (tmp_path / "raw_interventions.jsonl").write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8"
    )
    _write_json(tmp_path / "candidate_assessments.json", [
        {"candidate_id": candidate, "status": "rejected"} for candidate in candidates
    ])
    _write_json(tmp_path / "message_positive_controls.json", [{}] * 32)
    _write_json(tmp_path / "summary.json", {
        "run_id": "run", "candidate_execution_count": 1344,
        "message_positive_control_count": 32, "supported_candidates": [],
        "assessment_outcome": "no_internal_candidate_passed",
        "development_audit_executions": 0, "validation_executions": 0, "test_executions": 0,
        "query_ledger": {"executions": 1376, "maximum_executions": 1400,
                         "forward_steps": 5000, "maximum_forward_steps": 8000},
    })
    _write_json(tmp_path / "qci_preflight.json", {"decision": {"overall": "PASS"}})
    _write_json(tmp_path / "qci_model_access.json", {"state": "QCI_DISCOVERY_COMPLETE"})
    artifact_names = ["summary.json", "raw_interventions.jsonl", "candidate_assessments.json",
                      "message_positive_controls.json", "qci_preflight.json", "qci_model_access.json"]
    hashes = {str(tmp_path / name): hashlib.sha256((tmp_path / name).read_bytes()).hexdigest()
              for name in artifact_names}
    _write_json(tmp_path / "manifest.json", {"artifact_paths": hashes})
    archive_hashes = {name: hashlib.sha256((tmp_path / name).read_bytes()).hexdigest()
                      for name in artifact_names + ["manifest.json"]}
    _write_json(tmp_path / "archive_contents.json", archive_hashes)
    return candidates


def test_qci_bundle_verifier_accepts_complete_locked_bundle(tmp_path) -> None:
    _bundle(tmp_path)
    report = verify(tmp_path)
    assert report["overall"] == "PASS"
    assert report["candidate_execution_count"] == 1344
    assert report["validation_executions"] == report["test_executions"] == 0
    assert report["next_gate"] == "STOP_NO_SUPPORTED_CANDIDATE"


def test_qci_bundle_verifier_rejects_missing_denominator(tmp_path) -> None:
    _bundle(tmp_path)
    lines = (tmp_path / "raw_interventions.jsonl").read_text(encoding="utf-8").splitlines()
    (tmp_path / "raw_interventions.jsonl").write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="hash failures|denominator"):
        verify(tmp_path)


def test_qci_bundle_verifier_rejects_inconsistent_support_summary(tmp_path) -> None:
    _bundle(tmp_path)
    summary_path = tmp_path / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["supported_candidates"] = ["sender.node0"]
    summary["assessment_outcome"] = "supported_candidates_found"
    _write_json(summary_path, summary)
    manifest_path = tmp_path / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    recorded = next(key for key in manifest["artifact_paths"] if key.endswith("summary.json"))
    manifest["artifact_paths"][recorded] = hashlib.sha256(summary_path.read_bytes()).hexdigest()
    _write_json(manifest_path, manifest)
    archive_path = tmp_path / "archive_contents.json"
    archive = json.loads(archive_path.read_text(encoding="utf-8"))
    archive["summary.json"] = hashlib.sha256(summary_path.read_bytes()).hexdigest()
    archive["manifest.json"] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    _write_json(archive_path, archive)
    with pytest.raises(ValueError, match="support classification differs"):
        verify(tmp_path)
