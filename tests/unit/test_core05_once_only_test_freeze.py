"""Scientific-boundary tests for the CORE-05 proposal."""

from pathlib import Path

import pytest
import yaml

from causal.once_only_test_freeze import load_and_validate_once_only_test_freeze


ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = ROOT / "configs/phase1_core/core05_once_only_test_freeze_v1.yaml"


def _changed(tmp_path: Path, mutate) -> Path:
    value = yaml.safe_load(PROTOCOL.read_text(encoding="utf-8")); mutate(value)
    path = tmp_path / "core05.yaml"; path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")
    return path


def test_repository_core05_waits_for_review() -> None:
    protocol = load_and_validate_once_only_test_freeze(PROTOCOL, ROOT)
    assert protocol["attempt_control"]["once_only"] is True
    assert protocol["budget"]["maximum_model_forward_steps_total"] == 504


def test_test_cohort_drift_fails_closed(tmp_path: Path) -> None:
    path = _changed(tmp_path, lambda value: value["cohort"]["case_ids"].pop())
    with pytest.raises(PermissionError, match="cohort differs"):
        load_and_validate_once_only_test_freeze(path, ROOT)


def test_reselection_fails_closed(tmp_path: Path) -> None:
    path = _changed(tmp_path, lambda value: value["arms"][1].update({"component": "receiver.head.L22.H5.pre_o_proj"}))
    with pytest.raises(ValueError, match="repair differs"):
        load_and_validate_once_only_test_freeze(path, ROOT)


def test_threshold_drift_fails_closed(tmp_path: Path) -> None:
    path = _changed(tmp_path, lambda value: value["decision_rule"]["test_acceptance"].update({"minimum_attacked_decision_recovery_accuracy": 0.5}))
    with pytest.raises(ValueError, match="thresholds differ"):
        load_and_validate_once_only_test_freeze(path, ROOT)


def test_once_only_guard_cannot_be_removed(tmp_path: Path) -> None:
    path = _changed(tmp_path, lambda value: value["attempt_control"].update({"once_only": False}))
    with pytest.raises(PermissionError, match="once-only"):
        load_and_validate_once_only_test_freeze(path, ROOT)


def test_completed_attempt_cannot_be_rerun(tmp_path: Path) -> None:
    path = _changed(tmp_path, lambda value: value["attempt_control"].update({"fresh_rerun_after_complete_attempt": "allowed"}))
    with pytest.raises(PermissionError, match="cannot be rerun"):
        load_and_validate_once_only_test_freeze(path, ROOT)


def test_evidence_drift_fails_closed(tmp_path: Path) -> None:
    path = _changed(tmp_path, lambda value: value["evidence_inputs"]["core04_summary"].update({"sha256": "0" * 64}))
    with pytest.raises(ValueError, match="hash mismatch"):
        load_and_validate_once_only_test_freeze(path, ROOT)

