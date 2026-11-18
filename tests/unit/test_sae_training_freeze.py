"""Fail-closed tests for the prospective SAE training freeze."""

import json
from pathlib import Path

import pytest

from experiments.phase1.sae_training_freeze import load_and_validate_freeze


PROTOCOL = Path("configs/experiments/qwen_sae_training_freeze_v1.json")


def test_repository_protocol_is_valid_but_unapproved() -> None:
    protocol = load_and_validate_freeze(PROTOCOL)
    assert protocol["validation_executions"] == 0
    assert protocol["test_executions"] == 0
    with pytest.raises(PermissionError, match="human approval"):
        load_and_validate_freeze(PROTOCOL, require_approval=True)


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
