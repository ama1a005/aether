"""Tests for strict QCI-2A1 bundle verification."""

from __future__ import annotations

import hashlib
import json

from causal.qci2_execution import assess_semantic_candidate
from scripts.verify_qci2_bundle import EXPECTED_OPERATORS, EXPECTED_THRESHOLDS
from scripts.verify_qci2_audit_bundle import verify_audit


def _write(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")


def test_qci2_audit_verifier_recalculates_support(tmp_path) -> None:
    candidate = "receiver.module.L1.attention_output"
    effects = {"paired_rescue": .8, "paired_induction": .8, "same_decision_rescue": .78,
               "same_decision_induction": .78, "opposite_decision_rescue": .1,
               "opposite_decision_induction": .1, "irrelevant_position_rescue": .05,
               "identity_clean_to_clean": 0., "identity_attacked_to_attacked": 0., "passive_hook": 0.}
    rows = [{"candidate_id": candidate, "case_id": str(case), "operator": operator,
             "status": "ok", "hook_cleanup": True,
             "intervention_applications": 0 if operator == "passive_hook" else 1,
             "normalized_effect": effects[operator],
             "noninterference_pass": True if operator.startswith("identity_") or operator == "passive_hook" else None}
            for operator in EXPECTED_OPERATORS for case in range(4)]
    (tmp_path / "raw_audit_interventions.jsonl").write_text("\n".join(map(json.dumps, rows)) + "\n")
    assessment = assess_semantic_candidate(rows, EXPECTED_THRESHOLDS, expected_count=4)
    _write(tmp_path / "candidate_audit_assessments.json", [assessment]); _write(tmp_path / "message_positive_controls.json", [{}] * 8)
    _write(tmp_path / "summary.json", {"run_id": "audit", "candidate_ids": [candidate],
        "audit_supported_candidates": [candidate], "candidate_execution_count": 40,
        "message_positive_control_count": 8, "development_audit_executions": 48,
        "validation_executions": 0, "test_executions": 0, "next_state": "READY_FOR_QCI2_METHOD_FREEZE_REVIEW",
        "query_ledger": {"executions": 48, "maximum_executions": 500, "forward_steps": 100, "maximum_forward_steps": 2400}})
    _write(tmp_path / "audit_preflight.json", {"decision": {"overall": "PASS"}}); _write(tmp_path / "audit_model_access.json", {"state": "QCI2_AUDIT_COMPLETE"})
    names = ["summary.json", "raw_audit_interventions.jsonl", "candidate_audit_assessments.json", "message_positive_controls.json", "audit_preflight.json", "audit_model_access.json"]
    hashes = {str(tmp_path / name): hashlib.sha256((tmp_path / name).read_bytes()).hexdigest() for name in names}
    _write(tmp_path / "manifest.json", {"artifact_paths": hashes})
    _write(tmp_path / "archive_contents.json", {name: hashlib.sha256((tmp_path / name).read_bytes()).hexdigest() for name in names + ["manifest.json"]})
    report = verify_audit(tmp_path)
    assert report["overall"] == "PASS" and report["candidate_execution_count"] == 40
