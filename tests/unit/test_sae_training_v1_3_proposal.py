"""Fail-closed checks for the prospective SAE v1.3 semantics amendment."""

import json
from pathlib import Path

from causal.remediation_freeze import frozen_text_hash_matches


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "configs/experiments/qwen_sae_training_freeze_v1.json"
PARENT = ROOT / "configs/experiments/qwen_sae_training_freeze_v1_2_amendment.json"
PROPOSAL = ROOT / "configs/experiments/qwen_sae_training_freeze_v1_3_amendment.json"


def test_v1_3_is_review_gated_and_bound_to_approved_parent() -> None:
    proposal = json.loads(PROPOSAL.read_text(encoding="utf-8"))
    assert proposal["status"] == "awaiting_human_scientific_review"
    assert frozen_text_hash_matches(PARENT, proposal["parent_amendment_sha256"])
    assert proposal["human_review"]["approved"] is False


def test_v1_3_preserves_scientific_hyperparameters_and_thresholds() -> None:
    base = json.loads(BASE.read_text(encoding="utf-8"))
    proposal = json.loads(PROPOSAL.read_text(encoding="utf-8"))
    assert proposal["execution_semantics"]["maximum_epochs_unchanged"] == base["optimization"]["maximum_epochs"] == 100
    assert proposal["execution_semantics"]["posteligibility_patience"] == base["optimization"]["early_stopping_patience"] == 10
    unchanged = set(proposal["unchanged"])
    assert "optimizer_learning_rate_batch_size_l1_coefficient_and_loss" in unchanged
    assert "maximum_active_fraction_0_2" in unchanged
    assert "maximum_relative_reconstruction_error_0_1" in unchanged


def test_v1_3_retains_negative_results_and_protected_split_locks() -> None:
    proposal = json.loads(PROPOSAL.read_text(encoding="utf-8"))
    assert proposal["terminal_outcomes"]["all_three_seed_summaries_required_before_selection"] is True
    assert "SAE_REJECTED" in proposal["terminal_outcomes"]["selection_when_no_seed_is_eligible"]
    assert proposal["validation_executions"] == proposal["test_executions"] == 0
    assert "loosening_sparsity_or_reconstruction_thresholds" in proposal["prohibited"]
