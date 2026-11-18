"""Tests for real-Qwen trace Agent-C review semantics."""

from experiments.phase1.qwen_agent_c import evaluate


def test_agent_c_evaluator_preserves_invalid_rows_and_reviews_clean_vitals() -> None:
    registry = [{"case_id": "c", "split": "development", "features": {"spo2": 90},
                 "ground_truth_decision": "ESCALATE", "dataset_version": "v"}]
    rows = [{"case_id": "c", "clean_receiver_code": "A",
             "clean_message": {"valid": True, "decision_code": "A"},
             "attacked_receiver_code": "B",
             "attacked_message": {"valid": True, "decision_code": "B"}}]
    result = evaluate(rows, registry, 0.4)
    assert result["counts"] == {"total": 2, "valid": 2, "invalid": 0,
                                "incoming_correct": 1, "reviewed_correct": 2}
    assert {row["condition"] for row in result["rows"]} == {"clean", "attacked"}


def test_agent_c_rejects_validation_rows_and_duplicate_case_ids() -> None:
    registry = [{"case_id": "c", "split": "development", "features": {"spo2": 90},
                 "ground_truth_decision": "ESCALATE", "dataset_version": "v"},
                {"case_id": "v", "split": "validation", "features": {"spo2": 90},
                 "ground_truth_decision": "ESCALATE", "dataset_version": "v"}]
    row = {"case_id": "v", "clean_receiver_code": "A", "clean_message": {"valid": True},
           "attacked_receiver_code": "A", "attacked_message": {"valid": True}}
    import pytest
    with pytest.raises(ValueError, match="development registry"):
        evaluate([row], registry, 0.4)


def test_run_requires_approval_before_opening_inputs(tmp_path) -> None:
    import yaml
    import pytest
    from experiments.phase1.qwen_agent_c import run

    config = tmp_path / "proposal.yaml"
    config.write_text(yaml.safe_dump({
        "status": "awaiting_human_protocol_review", "split": "development",
        "validation_executions": 0, "test_executions": 0,
        "qwen_rows": "missing_rows.json", "case_registry": "missing_registry.json",
        "risk_score_threshold": 0.4,
    }), encoding="utf-8")
    with pytest.raises(PermissionError, match="human protocol decision is missing"):
        run(config, tmp_path / "missing_approval.json", tmp_path / "output")
    assert not (tmp_path / "output").exists()
