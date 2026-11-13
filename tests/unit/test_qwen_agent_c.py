"""Tests for real-Qwen trace Agent-C review semantics."""

from experiments.phase1.qwen_agent_c import evaluate


def test_agent_c_evaluator_preserves_invalid_rows_and_reviews_clean_vitals() -> None:
    registry = [{"case_id": "c", "split": "development", "features": {"spo2": 90},
                 "ground_truth_decision": "ESCALATE", "dataset_version": "v"}]
    rows = [{"case_id": "c", "attacked_receiver_code": "B",
             "attacked_message": {"valid": True, "decision_code": "B"}}]
    result = evaluate(rows, registry, 0.4)
    assert result["counts"] == {"total": 1, "valid": 1, "invalid": 0,
                                "incoming_correct": 0, "reviewed_correct": 1}
