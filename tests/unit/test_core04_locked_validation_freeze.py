"""Model-independent scientific-boundary tests for CORE-04."""

from pathlib import Path

import pytest
import yaml

from causal.locked_validation_freeze import load_and_validate_locked_validation_freeze


ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = ROOT / "configs/phase1_core/core04_locked_validation_freeze_v1.yaml"


def _changed(tmp_path: Path, mutate) -> Path:
    value = yaml.safe_load(PROTOCOL.read_text(encoding="utf-8"))
    mutate(value)
    path = tmp_path / "core04.yaml"
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")
    return path


def test_repository_core04_is_valid_and_waits_for_review() -> None:
    protocol = load_and_validate_locked_validation_freeze(PROTOCOL, ROOT)
    assert protocol["status"] == "AWAITING_HUMAN_REVIEW"
    assert protocol["decision_rule"]["no_arm_reselection"] is True
    assert protocol["budget"]["maximum_model_forward_steps_total"] == 504


def test_validation_cohort_drift_fails_closed(tmp_path: Path) -> None:
    path = _changed(tmp_path, lambda value: value["cohort"]["case_ids"].pop())
    with pytest.raises(PermissionError, match="cohort differs"):
        load_and_validate_locked_validation_freeze(path, ROOT)


@pytest.mark.parametrize("split", ["development_case_ids", "test_case_ids"])
def test_other_split_access_fails_closed(tmp_path: Path, split: str) -> None:
    path = _changed(tmp_path, lambda value: value["cohort"][split].append("forbidden"))
    with pytest.raises(PermissionError, match="development or test"):
        load_and_validate_locked_validation_freeze(path, ROOT)


def test_reselection_fails_closed(tmp_path: Path) -> None:
    path = _changed(tmp_path, lambda value: value["decision_rule"].update({"no_arm_reselection": False}))
    with pytest.raises(PermissionError, match="reselect"):
        load_and_validate_locked_validation_freeze(path, ROOT)


def test_selected_component_drift_fails_closed(tmp_path: Path) -> None:
    path = _changed(tmp_path, lambda value: value["arms"][1].update({"component": "receiver.head.L22.H5.pre_o_proj"}))
    with pytest.raises(ValueError, match="component differs"):
        load_and_validate_locked_validation_freeze(path, ROOT)


def test_invalid_rows_cannot_be_removed(tmp_path: Path) -> None:
    path = _changed(tmp_path, lambda value: value["endpoints"]["primary_security"].update({"denominator": "valid_only"}))
    with pytest.raises(ValueError, match="drops protected"):
        load_and_validate_locked_validation_freeze(path, ROOT)


def test_oracle_dependency_cannot_be_hidden(tmp_path: Path) -> None:
    path = _changed(tmp_path, lambda value: value["intervention_semantics"].update({"deployable_without_oracle": True}))
    with pytest.raises(ValueError, match="oracle-free"):
        load_and_validate_locked_validation_freeze(path, ROOT)


def test_budget_drift_fails_closed(tmp_path: Path) -> None:
    path = _changed(tmp_path, lambda value: value["budget"].update({"maximum_model_forward_steps_total": 505}))
    with pytest.raises(ValueError, match="total budget"):
        load_and_validate_locked_validation_freeze(path, ROOT)


def test_evidence_hash_drift_fails_closed(tmp_path: Path) -> None:
    path = _changed(tmp_path, lambda value: value["evidence_inputs"]["core03_summary"].update({"sha256": "0" * 64}))
    with pytest.raises(ValueError, match="hash mismatch"):
        load_and_validate_locked_validation_freeze(path, ROOT)


def test_review_gate_blocks_implementation(tmp_path: Path) -> None:
    path = _changed(tmp_path, lambda value: value["review"].update({"implementation_before_approval": "allowed"}))
    with pytest.raises(PermissionError, match="await approval"):
        load_and_validate_locked_validation_freeze(path, ROOT)

