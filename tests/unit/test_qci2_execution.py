"""QCI-2 semantic-control tests use constructed rows only."""

from causal.qci2_execution import assess_semantic_candidate, semantic_donor_mappings
from instrumentation.run_qwen_causal_semantic_interventions import _load_inputs


OPERATORS = (
    "paired_rescue", "paired_induction", "same_decision_rescue",
    "same_decision_induction", "opposite_decision_rescue",
    "opposite_decision_induction", "irrelevant_position_rescue",
    "identity_clean_to_clean", "identity_attacked_to_attacked", "passive_hook",
)


def test_semantic_donors_separate_generalization_from_contrast() -> None:
    rows = [
        {"case_id": "a1", "direction": "A_TO_B"},
        {"case_id": "a2", "direction": "A_TO_B"},
        {"case_id": "b1", "direction": "B_TO_A"},
        {"case_id": "b2", "direction": "B_TO_A"},
    ]
    mappings = semantic_donor_mappings(rows)
    assert mappings["same_decision"] == {"a1": "a2", "a2": "a1", "b1": "b2", "b2": "b1"}
    assert mappings["opposite_decision"] == {"a1": "b1", "a2": "b2", "b1": "a1", "b2": "a2"}


def test_qci2_inputs_reuse_candidates_and_keep_audit_closed() -> None:
    protocol, rows, candidates = _load_inputs()
    assert protocol["protocol_version"] == "QCI-2.0"
    assert len(rows) == 16 and len(candidates) == 12
    assert not set(protocol["discovery_case_ids"]) & set(protocol["development_audit_case_ids"])
    assert protocol["budget"]["candidate_executions"] == 1920


def test_semantic_candidate_requires_generalization_and_opposite_contrast() -> None:
    values = {
        "paired_rescue": 0.8, "paired_induction": 0.8,
        "same_decision_rescue": 0.76, "same_decision_induction": 0.75,
        "opposite_decision_rescue": 0.1, "opposite_decision_induction": 0.1,
        "irrelevant_position_rescue": 0.05,
    }
    rows = []
    for operator in OPERATORS:
        for case in range(4):
            rows.append({
                "candidate_id": "receiver.head.L1.H0.pre_o_proj", "case_id": str(case),
                "operator": operator, "status": "ok",
                "normalized_effect": values.get(operator, 0.0),
                "noninterference_pass": operator.startswith("identity_") or operator == "passive_hook",
            })
    thresholds = {
        "median_effect_min": 0.5, "consistency_min": 0.75,
        "same_decision_gap_max": 0.1, "opposite_decision_contrast_min": 0.2,
        "position_contrast_min": 0.2,
    }
    result = assess_semantic_candidate(rows, thresholds, expected_count=4)
    assert result["status"] == "supported"
    rows_by_operator = [row for row in rows if row["operator"] != "opposite_decision_rescue"]
    rows_by_operator.extend({**row, "normalized_effect": 0.75} for row in rows if row["operator"] == "opposite_decision_rescue")
    rejected = assess_semantic_candidate(rows_by_operator, thresholds, expected_count=4)
    assert rejected["status"] == "rejected"
    assert "opposite_rescue_contrast" in rejected["reasons"]
