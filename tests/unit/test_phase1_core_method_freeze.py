"""Fail-closed tests for the QCI-2 method-freeze proposal."""

from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from causal.method_freeze import (
    BudgetExhausted,
    MatchedBudgetLedger,
    edge_record_is_acceptable,
    load_and_validate_amendment,
    load_and_validate_v2_2_amendment,
    load_and_validate_proposal,
    proposal_sha256,
    validate_mask,
)


ROOT = Path(__file__).resolve().parents[2]
V1_PROPOSAL = ROOT / "configs/phase1_core/qci2_method_freeze_v1.yaml"
PROPOSAL = ROOT / "configs/phase1_core/qci2_method_freeze_v2.yaml"
AMENDMENT = ROOT / "configs/phase1_core/qci2_method_freeze_v2_1_amendment.yaml"
AMENDMENT_V2_2 = ROOT / "configs/phase1_core/qci2_method_freeze_v2_2_amendment.yaml"


def _write(tmp_path: Path, value: dict) -> Path:
    path = tmp_path / "proposal.yaml"
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")
    return path


def test_previous_proposal_is_immutable_and_distinct() -> None:
    assert proposal_sha256(V1_PROPOSAL) == "aafc0a20a33b0cabab1f9d54ceb2da42369c8fe617d2c4c620e5ee6fb4963d24"
    assert proposal_sha256(V1_PROPOSAL) != proposal_sha256(PROPOSAL)


def test_revised_repository_proposal_is_valid_but_not_reviewed() -> None:
    proposal = load_and_validate_proposal(PROPOSAL, ROOT)
    assert proposal["status"] == "AWAITING_HUMAN_REVIEW"
    assert proposal["validation_case_ids"] == []
    assert proposal["test_case_ids"] == []


@pytest.mark.parametrize("field", ["case_ids", "validation_case_ids", "test_case_ids"])
def test_locked_or_audit_case_access_fails_closed(tmp_path: Path, field: str) -> None:
    proposal = yaml.safe_load(PROPOSAL.read_text(encoding="utf-8"))
    changed = deepcopy(proposal)
    changed[field] = ["v2_case_010"]
    with pytest.raises(PermissionError):
        load_and_validate_proposal(_write(tmp_path, changed), ROOT)


def test_candidate_reselection_fails_closed(tmp_path: Path) -> None:
    proposal = yaml.safe_load(PROPOSAL.read_text(encoding="utf-8"))
    proposal["candidate_graph"]["nodes"][0]["id"] = "sender.module.L21.attention_output"
    with pytest.raises(ValueError, match="candidate set differs"):
        load_and_validate_proposal(_write(tmp_path, proposal), ROOT)


def test_supported_edge_cannot_be_asserted_by_proposal(tmp_path: Path) -> None:
    proposal = yaml.safe_load(PROPOSAL.read_text(encoding="utf-8"))
    proposal["candidate_graph"]["edges"][0]["status"] = "supported"
    with pytest.raises(ValueError, match="cannot pre-label"):
        load_and_validate_proposal(_write(tmp_path, proposal), ROOT)


def test_evidence_hash_drift_fails_closed(tmp_path: Path) -> None:
    proposal = yaml.safe_load(PROPOSAL.read_text(encoding="utf-8"))
    proposal["evidence_inputs"]["qci2_audit_summary"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="hash mismatch"):
        load_and_validate_proposal(_write(tmp_path, proposal), ROOT)


def test_legacy_message_bridge_is_never_scientific_evidence() -> None:
    from causal.bridge.message_bridge import MessageBridge

    bridge = MessageBridge()
    result = bridge.to_dict()
    assert result["scientific_evidence_eligible"] is False
    assert result["evidence_class"] == "synthetic_association_scaffold"


def test_mask_has_exact_order_and_nonselected_attacked_semantics() -> None:
    proposal = load_and_validate_proposal(PROPOSAL, ROOT)
    ordered = validate_mask(proposal, [
        "receiver.head.L20.H5.pre_o_proj",
        "sender.module.L22.attention_output",
        "message.decision_code",
    ])
    assert ordered == (
        "sender.module.L22.attention_output",
        "message.decision_code",
        "receiver.head.L20.H5.pre_o_proj",
    )
    assert proposal["mask_semantics"]["nonselected_components"] == "attacked_run_values_unchanged"


@pytest.mark.parametrize("overlap", [
    ["message.decision_code", "message.whole"],
    ["receiver.head.L22.H7.pre_o_proj", "receiver.module.L22.attention_output"],
])
def test_overlapping_masks_fail_before_model_access(overlap: list[str]) -> None:
    proposal = load_and_validate_proposal(PROPOSAL, ROOT)
    with pytest.raises(ValueError, match="overlapping interventions"):
        validate_mask(proposal, overlap)


def test_edges_and_outcome_are_not_mask_actions() -> None:
    proposal = load_and_validate_proposal(PROPOSAL, ROOT)
    with pytest.raises(ValueError, match="non-intervenable"):
        validate_mask(proposal, ["receiver.outcome_margin"])
    assert proposal["mask_semantics"]["edge_semantics"]["search_action"] is False


def test_budget_ledger_counts_all_phases_and_exhausts_fail_closed() -> None:
    ledger = MatchedBudgetLedger(2, 2, 96)
    ledger.consume(phase="baselines", mask=(), forward_steps=32, mask_evaluation=False)
    ledger.consume(phase="search", mask=("a",), forward_steps=32, search_mask=True)
    ledger.consume(phase="independent_verification", mask=("a",), forward_steps=32)
    assert ledger.mask_evaluations == 2
    assert ledger.phase_counts == {"baselines": 1, "search": 1, "independent_verification": 1}
    with pytest.raises(BudgetExhausted):
        ledger.consume(phase="local_minimality", mask=(), forward_steps=1)
    assert ledger.state == "INCOMPLETE_BUDGET"
    with pytest.raises(BudgetExhausted):
        ledger.complete()


def test_unique_mask_limit_is_independent_of_cached_revisits() -> None:
    ledger = MatchedBudgetLedger(1, 4, 128)
    ledger.consume(phase="ppo_training", mask=("a",), forward_steps=32, search_mask=True)
    ledger.consume(phase="ppo_training", mask=("a",), forward_steps=0, search_mask=True)
    with pytest.raises(BudgetExhausted):
        ledger.consume(phase="ppo_training", mask=("b",), forward_steps=32, search_mask=True)


def test_benign_metric_has_raw_logit_units_and_is_not_utility() -> None:
    proposal = load_and_validate_proposal(PROPOSAL, ROOT)
    metric = proposal["benign_noninterference"]
    assert metric["units"] == "raw_A_minus_B_logit_margin"
    assert metric["maximum"] == 0.1
    assert metric["is_benign_utility"] is False
    assert metric["separate_reports"]["clean_decision_accuracy"] is True


def test_edge_promotion_requires_real_complete_controlled_record() -> None:
    proposal = load_and_validate_proposal(PROPOSAL, ROOT)
    rule = proposal["bvp_edge_acceptance"]["e_s22_decision"]
    record = {
        "evidence_type": "real_model_intervention",
        "incoming_message_policy": rule["incoming_message_policy"],
        "effect_direction": rule["effect_direction"],
        "controls_passed": list(rule["controls"]),
        "eligible_count": 16,
        "invalid_or_error_count": 0,
        "median_normalized_recovery": 0.6,
        "consistency_fraction": 0.8,
        "opposite_contrast": 0.3,
        "position_contrast": 0.3,
    }
    assert edge_record_is_acceptable(rule, record)
    record["evidence_type"] = "association"
    assert not edge_record_is_acceptable(rule, record)
    record["evidence_type"] = "real_model_intervention"
    record["controls_passed"].remove("opposite_decision_donor")
    assert not edge_record_is_acceptable(rule, record)


def test_construct_stress_test_is_separate_and_unexecuted() -> None:
    proposal = load_and_validate_proposal(PROPOSAL, ROOT)
    stress = proposal["construct_validity"]["separate_stress_protocol"]
    assert stress["status"] == "PROSPECTIVE_NOT_EXECUTED"
    assert stress["input_policy"].startswith("new_development_cases_disjoint")
    assert proposal["construct_validity"]["qci2_prompts_cases_thresholds_results_unchanged"] is True


def test_accounting_amendment_matches_qualified_generation_steps() -> None:
    amendment = load_and_validate_amendment(AMENDMENT, PROPOSAL, ROOT)
    correction = amendment["forward_accounting_correction"]
    assert correction["model_forwards_per_mask_evaluation"] == 16 * (4 + 1)
    assert correction["maximum_model_forward_steps"] == 160 + 45 * 80
    assert amendment["scientific_method_changes"] == "none_accounting_only"


def test_accounting_amendment_cannot_change_method(tmp_path: Path) -> None:
    amendment = yaml.safe_load(AMENDMENT.read_text(encoding="utf-8"))
    amendment["scientific_method_changes"] = "changed_candidates"
    with pytest.raises(ValueError, match="accounting only"):
        load_and_validate_amendment(_write(tmp_path, amendment), PROPOSAL, ROOT)


def test_v2_2_counts_attack_and_clean_identity_conditions() -> None:
    amendment = load_and_validate_v2_2_amendment(AMENDMENT_V2_2, PROPOSAL, AMENDMENT, ROOT)
    correction = amendment["forward_accounting_correction"]
    assert correction["model_forwards_per_mask_evaluation"] == 16 * 2 * (4 + 1)
    assert correction["maximum_model_forward_steps"] == 160 + 45 * 160


def test_v2_2_cannot_omit_benign_condition(tmp_path: Path) -> None:
    amendment = yaml.safe_load(AMENDMENT_V2_2.read_text(encoding="utf-8"))
    amendment["forward_accounting_correction"]["conditions_per_mask_evaluation"] = 1
    with pytest.raises(ValueError, match="attack and benign"):
        load_and_validate_v2_2_amendment(_write(tmp_path, amendment), PROPOSAL, AMENDMENT, ROOT)
