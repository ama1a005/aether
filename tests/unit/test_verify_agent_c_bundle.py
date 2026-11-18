"""Independent verifier boundary tests for retained-trace Agent C bundles."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import scripts.verify_agent_c_bundle as verifier
from experiments.external_bundle import VerifiedBundle


def _write_candidate_bundle(root: Path) -> None:
    """Create verifier-only metadata and source-backed paired rows."""
    root.mkdir()
    rows = []
    for index in range(24):
        case_id = f"case-{index:02d}"
        source = {"case_id": case_id, "split": "development", "eligible": True,
                  "ground_truth_decision": "ESCALATE", "ground_truth_code": "A"}
        for condition in ("clean", "attacked"):
            source.update({
                f"{condition}_message": {"valid": True},
                f"{condition}_message_valid": True,
                f"{condition}_receiver_code": "A",
                f"{condition}_receiver_prompt": "retained prompt",
                f"{condition}_receiver_prompt_token_ids": [1, 2],
            })
            rows.append({
                "case_id": case_id,
                "condition": condition,
                "source_row": dict(source),
                "input": {
                    "message": source[f"{condition}_message"],
                    "receiver_code": "A",
                    "receiver_prompt": "retained prompt",
                    "receiver_prompt_token_ids": [1, 2],
                },
                "valid": True,
                "incoming_decision": "ESCALATE",
                "reviewed_decision": "ESCALATE",
                "ground_truth_decision": "ESCALATE",
                "incoming_correct": True,
                "reviewed_correct": True,
                "tool_calls": [],
                "review": {"incoming_decision": "ESCALATE",
                           "reviewed_decision": "ESCALATE", "tool_calls": []},
                "latency_ms": 0.5,
            })
    counts = {"total": 48, "valid": 48, "invalid": 0,
              "incoming_correct": 48, "reviewed_correct": 48}
    (root / "raw_reviews.json").write_text(
        json.dumps({"rows": rows, "counts": counts}), encoding="utf-8")
    (root / "summary.json").write_text(json.dumps({
        "overall": "SUPPORTING_EVIDENCE_ONLY",
        **counts,
        "validation_executions": 0,
        "test_executions": 0,
    }), encoding="utf-8")
    (root / "bundle_manifest.json").write_text(json.dumps({
        "validation_executions": 0,
        "test_executions": 0,
    }), encoding="utf-8")


def test_agent_c_verifier_accepts_exact_development_pairing(tmp_path, monkeypatch) -> None:
    root = tmp_path / "bundle"
    _write_candidate_bundle(root)
    monkeypatch.setattr(verifier, "verify_bundle", lambda *args, **kwargs:
                        VerifiedBundle("agent-c", "run-1", "qwen_agent_c", 2))

    result = verifier.verify(root)

    assert result["verified"] is True
    assert result["case_count"] == 24
    assert result["condition_rows"] == 48


def test_agent_c_verifier_rejects_summary_metrics_not_derived_from_raw(tmp_path, monkeypatch) -> None:
    root = tmp_path / "bundle"
    _write_candidate_bundle(root)
    monkeypatch.setattr(verifier, "verify_bundle", lambda *args, **kwargs:
                        VerifiedBundle("agent-c", "run-1", "qwen_agent_c", 2))
    summary = json.loads((root / "summary.json").read_text(encoding="utf-8"))
    summary["reviewed_correct"] = 47
    (root / "summary.json").write_text(json.dumps(summary), encoding="utf-8")

    with pytest.raises(ValueError, match="metrics differ"):
        verifier.verify(root)


def test_agent_c_verifier_rejects_missing_case_condition(tmp_path, monkeypatch) -> None:
    root = tmp_path / "bundle"
    _write_candidate_bundle(root)
    monkeypatch.setattr(verifier, "verify_bundle", lambda *args, **kwargs:
                        VerifiedBundle("agent-c", "run-1", "qwen_agent_c", 2))
    raw = json.loads((root / "raw_reviews.json").read_text(encoding="utf-8"))
    raw["rows"].pop()
    raw["counts"]["total"] = 47
    raw["counts"]["valid"] = 47
    (root / "raw_reviews.json").write_text(json.dumps(raw), encoding="utf-8")

    with pytest.raises(ValueError, match="exactly 48"):
        verifier.verify(root)
