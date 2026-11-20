"""Fail-closed scientific checks for real-Qwen red-team bundles."""

import pytest

from scripts.verify_qwen_red_team_bundle import _validate_summary


def _summary(*, errors: int, conditional: int) -> dict:
    return {
        "overall": "PASS",
        "evidence_class": "real_qwen_development_red_team",
        "validation_executions": 0,
        "test_executions": 0,
        "campaign": {
            "target_calls": 96,
            "overall": {
                "eligible_attempts": 48,
                "errors": errors,
                "conditional_eligible": conditional,
            },
        },
    }


def test_red_team_summary_accepts_usable_frozen_campaign() -> None:
    _validate_summary(_summary(errors=2, conditional=20), 48)


def test_red_team_summary_rejects_error_only_and_zero_eligible_runs() -> None:
    with pytest.raises(ValueError, match="no usable error denominator"):
        _validate_summary(_summary(errors=48, conditional=0), 48)
    with pytest.raises(ValueError, match="no clean-correct"):
        _validate_summary(_summary(errors=2, conditional=0), 48)


def test_red_team_summary_rejects_partial_or_protected_runs() -> None:
    with pytest.raises(ValueError, match="attempt count"):
        _validate_summary(_summary(errors=0, conditional=20), 47)
    protected = _summary(errors=0, conditional=20)
    protected["validation_executions"] = 1
    with pytest.raises(ValueError, match="protected split"):
        _validate_summary(protected, 48)
