"""Fail-closed tests for the prospective SAE training freeze."""

import json
from pathlib import Path

import pytest

from experiments.phase1.sae_training_freeze import (
    load_and_validate_amendment,
    load_and_validate_freeze,
    load_and_validate_v1_2_amendment,
    load_and_validate_v1_3_amendment,
    verify_human_decision,
)


PROTOCOL = Path("configs/experiments/qwen_sae_training_freeze_v1.json")
AMENDMENT = Path("configs/experiments/qwen_sae_training_freeze_v1_1_amendment.json")
AMENDMENT_V1_2 = Path("configs/experiments/qwen_sae_training_freeze_v1_2_amendment.json")
AMENDMENT_V1_3 = Path("configs/experiments/qwen_sae_training_freeze_v1_3_amendment.json")
DECISION = Path("results/phase1/sae_training_freeze/decision.json")


def test_repository_protocol_is_valid_but_unapproved() -> None:
    protocol = load_and_validate_freeze(PROTOCOL)
    assert protocol["validation_executions"] == 0
    assert protocol["test_executions"] == 0
    with pytest.raises(PermissionError, match="human approval"):
        load_and_validate_freeze(PROTOCOL, require_approval=True)


def test_separate_human_decision_matches_immutable_v1() -> None:
    decision = verify_human_decision(PROTOCOL, DECISION)
    assert decision["proposal_sha256"] == "5dd220297a159a712e114489ca8872ab0a7badf258e410e0ddffa65883ce1272"


def test_overlapping_partitions_are_rejected(tmp_path) -> None:
    raw = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    raw["audit_case_ids"][0] = raw["train_case_ids"][0]
    candidate = tmp_path / "bad.json"
    candidate.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="overlap"):
        load_and_validate_freeze(candidate)


def test_underdetermined_training_matrix_is_rejected(tmp_path) -> None:
    raw = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    raw["minimum_training_rows"] = 40
    candidate = tmp_path / "bad.json"
    candidate.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="underdetermined"):
        load_and_validate_freeze(candidate)


def test_v1_1_amendment_preserves_minimum_and_protected_split_locks() -> None:
    amendment = load_and_validate_amendment(AMENDMENT, PROTOCOL)
    assert amendment["training_corpus"]["training_token_count"] == 57344
    assert amendment["training_corpus"]["protected_aether_cases_used_for_training"] == []
    with pytest.raises(PermissionError, match="human approval"):
        load_and_validate_amendment(AMENDMENT, PROTOCOL, require_approval=True)


def test_v1_1_amendment_cannot_weaken_training_rows(tmp_path) -> None:
    raw = json.loads(AMENDMENT.read_text(encoding="utf-8"))
    raw["training_corpus"]["training_token_count"] = 9000
    raw["training_corpus"]["checkpoint_selection_token_count"] = 56536
    candidate = tmp_path / "bad.json"
    candidate.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="corpus mismatch|weakens"):
        load_and_validate_amendment(candidate, PROTOCOL)


def test_v1_1_amendment_cannot_change_aether_audit_cases(tmp_path) -> None:
    raw = json.loads(AMENDMENT.read_text(encoding="utf-8"))
    raw["aether_final_audit"]["case_ids"][0] = "v2_case_002"
    candidate = tmp_path / "bad.json"
    candidate.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="audit cases"):
        load_and_validate_amendment(candidate, PROTOCOL)


def test_v1_2_changes_only_the_pinned_retrieval_revision() -> None:
    amendment = load_and_validate_v1_2_amendment(AMENDMENT_V1_2, AMENDMENT, PROTOCOL)
    assert amendment["correction"]["dataset_revision"] == "b08601e04326c79dfdd32d625aee71d232d685c3"
    assert amendment["validation_executions"] == amendment["test_executions"] == 0
    with pytest.raises(PermissionError, match="human approval"):
        load_and_validate_v1_2_amendment(
            AMENDMENT_V1_2, AMENDMENT, PROTOCOL, require_approval=True
        )


def test_v1_2_rejects_unreviewed_file_hash_change(tmp_path) -> None:
    raw = json.loads(AMENDMENT_V1_2.read_text(encoding="utf-8"))
    raw["correction"]["source_file_sha256"] = "0" * 64
    candidate = tmp_path / "bad.json"
    candidate.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="retrieval mismatch"):
        load_and_validate_v1_2_amendment(candidate, AMENDMENT, PROTOCOL)


def test_v1_3_changes_only_execution_and_negative_result_semantics() -> None:
    amendment = load_and_validate_v1_3_amendment(
        AMENDMENT_V1_3, AMENDMENT_V1_2, AMENDMENT, PROTOCOL
    )
    assert amendment["execution_semantics"]["preeligibility_early_stopping"] == "forbidden"
    assert amendment["execution_semantics"]["maximum_epochs_unchanged"] == 100
    assert amendment["validation_executions"] == amendment["test_executions"] == 0


def test_v1_3_rejects_threshold_or_epoch_drift(tmp_path) -> None:
    raw = json.loads(AMENDMENT_V1_3.read_text(encoding="utf-8"))
    raw["execution_semantics"]["maximum_epochs_unchanged"] = 10
    candidate = tmp_path / "bad.json"
    candidate.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="maximum epochs"):
        load_and_validate_v1_3_amendment(
            candidate, AMENDMENT_V1_2, AMENDMENT, PROTOCOL
        )
