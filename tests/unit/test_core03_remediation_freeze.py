"""Model-independent scientific-boundary tests for CORE-03."""

from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from causal.remediation_freeze import load_and_validate_remediation_freeze


ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = ROOT / "configs/phase1_core/core03_remediation_freeze_v1.yaml"


def _changed(tmp_path: Path, mutate) -> Path:
    value = yaml.safe_load(PROTOCOL.read_text(encoding="utf-8"))
    mutate(value)
    path = tmp_path / "core03.yaml"
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")
    return path


def test_repository_core03_is_valid_and_waits_for_review() -> None:
    protocol = load_and_validate_remediation_freeze(PROTOCOL, ROOT)
    assert protocol["status"] == "AWAITING_HUMAN_REVIEW"
    assert protocol["intervention_semantics"]["deployable_without_oracle"] is False
    assert protocol["budget"]["maximum_model_forward_steps_total"] == 624


@pytest.mark.parametrize("split", ["validation_case_ids", "test_case_ids"])
def test_protected_split_access_fails_closed(tmp_path: Path, split: str) -> None:
    path = _changed(tmp_path, lambda value: value["cohort"][split].append("forbidden"))
    with pytest.raises(PermissionError, match="validation or test"):
        load_and_validate_remediation_freeze(path, ROOT)


def test_arm_reselection_fails_closed(tmp_path: Path) -> None:
    path = _changed(tmp_path, lambda value: value["arms"].pop())
    with pytest.raises(ValueError, match="arm set"):
        load_and_validate_remediation_freeze(path, ROOT)


def test_oracle_dependency_cannot_be_hidden(tmp_path: Path) -> None:
    path = _changed(
        tmp_path,
        lambda value: value["intervention_semantics"].update({"deployable_without_oracle": True}),
    )
    with pytest.raises(ValueError, match="deployable"):
        load_and_validate_remediation_freeze(path, ROOT)


def test_invalid_rows_cannot_be_removed_from_denominator(tmp_path: Path) -> None:
    path = _changed(
        tmp_path,
        lambda value: value["endpoints"]["primary_security"].update(
            {"denominator": "valid_rows_only"}
        ),
    )
    with pytest.raises(ValueError, match="silently drops"):
        load_and_validate_remediation_freeze(path, ROOT)


def test_budget_drift_fails_closed(tmp_path: Path) -> None:
    path = _changed(
        tmp_path,
        lambda value: value["budget"].update({"maximum_model_forward_steps_total": 625}),
    )
    with pytest.raises(ValueError, match="total budget"):
        load_and_validate_remediation_freeze(path, ROOT)


def test_evidence_hash_drift_fails_closed(tmp_path: Path) -> None:
    path = _changed(
        tmp_path,
        lambda value: value["evidence_inputs"]["core02_summary"].update({"sha256": "0" * 64}),
    )
    with pytest.raises(ValueError, match="hash mismatch"):
        load_and_validate_remediation_freeze(path, ROOT)


def test_review_gate_cannot_authorize_model_access(tmp_path: Path) -> None:
    path = _changed(
        tmp_path,
        lambda value: value["review"].update({"model_access_before_approval": "allowed"}),
    )
    with pytest.raises(PermissionError, match="await exact-hash approval"):
        load_and_validate_remediation_freeze(path, ROOT)

