"""Tests for the prospective SmolLM2 qualification freeze."""

import json
from pathlib import Path

import pytest

from paired_trace.secondary_model_freeze import load_and_validate


ROOT = Path(__file__).resolve().parents[2]
PROPOSAL = ROOT / "configs/model_qualification/smollm2_1_7b_second_model_freeze_v1.json"


def test_repository_proposal_is_valid_and_protected() -> None:
    proposal = load_and_validate(PROPOSAL, ROOT)
    assert proposal["model"]["expected_layer_count"] == 24
    assert proposal["validation_executions"] == proposal["test_executions"] == 0


def test_primary_model_is_rejected(tmp_path) -> None:
    raw = json.loads(PROPOSAL.read_text(encoding="utf-8"))
    raw["model"]["model_id"] = "Qwen/Qwen2.5-1.5B-Instruct"
    candidate = tmp_path / "bad.json"; candidate.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="primary|disqualified"):
        load_and_validate(candidate, ROOT)


def test_protected_split_access_is_rejected(tmp_path) -> None:
    raw = json.loads(PROPOSAL.read_text(encoding="utf-8")); raw["test_executions"] = 1
    candidate = tmp_path / "bad.json"; candidate.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(PermissionError, match="protected split"):
        load_and_validate(candidate, ROOT)


def test_frozen_input_hash_drift_is_rejected(tmp_path) -> None:
    raw = json.loads(PROPOSAL.read_text(encoding="utf-8")); raw["behavioral_qualification"]["cases_sha256"] = "0" * 64
    candidate = tmp_path / "bad.json"; candidate.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="input mismatch"):
        load_and_validate(candidate, ROOT)
