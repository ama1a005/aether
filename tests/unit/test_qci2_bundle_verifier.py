"""Tests for strict QCI-2 evidence verification and ingestion."""

from __future__ import annotations

import hashlib
import json

import pytest

from causal.qci2_execution import assess_semantic_candidate
from scripts.ingest_qci2_bundle import ingest
from scripts.verify_qci2_bundle import EXPECTED_OPERATORS, EXPECTED_THRESHOLDS, verify


def _write(path, value) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def _bundle(root) -> list[str]:
    candidates = [f"{'sender' if index < 6 else 'receiver'}.node{index}" for index in range(12)]
    rows = []
    effect = {
        "paired_rescue": 0.8, "paired_induction": 0.8,
        "same_decision_rescue": 0.78, "same_decision_induction": 0.78,
        "opposite_decision_rescue": 0.1, "opposite_decision_induction": 0.1,
        "irrelevant_position_rescue": 0.05,
        "identity_clean_to_clean": 0.0, "identity_attacked_to_attacked": 0.0,
        "passive_hook": 0.0,
    }
    for candidate in candidates:
        for operator in sorted(EXPECTED_OPERATORS):
            for case in range(16):
                rows.append({
                    "candidate_id": candidate, "case_id": str(case), "operator": operator,
                    "status": "ok", "hook_cleanup": True,
                    "intervention_applications": 0 if operator == "passive_hook" else 1,
                    "normalized_effect": effect[operator],
                    "noninterference_pass": True if operator.startswith("identity_") or operator == "passive_hook" else None,
                })
    raw = root / "raw_interventions.jsonl"
    raw.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    assessments = [
        assess_semantic_candidate([row for row in rows if row["candidate_id"] == candidate], EXPECTED_THRESHOLDS)
        for candidate in candidates
    ]
    _write(root / "candidate_assessments.json", assessments)
    _write(root / "message_positive_controls.json", [{}] * 32)
    _write(root / "summary.json", {
        "run_id": "qci2", "candidate_execution_count": 1920,
        "message_positive_control_count": 32, "supported_candidates": candidates,
        "assessment_outcome": "supported_candidates_found",
        "development_audit_executions": 0, "validation_executions": 0, "test_executions": 0,
        "query_ledger": {"executions": 1952, "maximum_executions": 2000,
                         "forward_steps": 7000, "maximum_forward_steps": 8000},
    })
    _write(root / "qci2_preflight.json", {"decision": {"overall": "PASS"}})
    _write(root / "qci2_model_access.json", {"state": "QCI2_DISCOVERY_COMPLETE"})
    artifacts = ["summary.json", "raw_interventions.jsonl", "candidate_assessments.json",
                 "message_positive_controls.json", "qci2_preflight.json", "qci2_model_access.json"]
    hashes = {str(root / name): hashlib.sha256((root / name).read_bytes()).hexdigest() for name in artifacts}
    _write(root / "manifest.json", {"artifact_paths": hashes})
    archive_hashes = {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                      for name in artifacts + ["manifest.json"]}
    _write(root / "archive_contents.json", archive_hashes)
    return candidates


def test_qci2_verifier_recalculates_and_accepts_complete_bundle(tmp_path) -> None:
    candidates = _bundle(tmp_path)
    report = verify(tmp_path)
    assert report["overall"] == "PASS"
    assert report["candidate_execution_count"] == 1920
    assert report["supported_candidates"] == sorted(candidates)
    assert report["next_gate"] == "ELIGIBLE_TO_FREEZE_QCI2_DEVELOPMENT_AUDIT"


def test_qci2_verifier_rejects_tampered_assessment(tmp_path) -> None:
    _bundle(tmp_path)
    assessments = json.loads((tmp_path / "candidate_assessments.json").read_text(encoding="utf-8"))
    assessments[0]["status"] = "rejected"
    _write(tmp_path / "candidate_assessments.json", assessments)
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    key = next(key for key in manifest["artifact_paths"] if key.endswith("candidate_assessments.json"))
    manifest["artifact_paths"][key] = hashlib.sha256((tmp_path / "candidate_assessments.json").read_bytes()).hexdigest()
    _write(tmp_path / "manifest.json", manifest)
    contents = json.loads((tmp_path / "archive_contents.json").read_text(encoding="utf-8"))
    contents["candidate_assessments.json"] = hashlib.sha256((tmp_path / "candidate_assessments.json").read_bytes()).hexdigest()
    contents["manifest.json"] = hashlib.sha256((tmp_path / "manifest.json").read_bytes()).hexdigest()
    _write(tmp_path / "archive_contents.json", contents)
    with pytest.raises(ValueError, match="independent recalculation"):
        verify(tmp_path)


def test_qci2_ingest_is_atomic_and_refuses_overwrite(tmp_path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    _bundle(source)
    destination = tmp_path / "accepted" / "qci2"
    receipt = ingest(source, destination)
    assert receipt["verification"]["overall"] == "PASS"
    assert (destination / "ingest_receipt.json").is_file()
    with pytest.raises(FileExistsError, match="already exists"):
        ingest(source, destination)
