"""Tests for prospective QCI development-audit planning."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from causal.qci_audit import build_audit_plan


ROOT = Path(__file__).resolve().parents[2]


def _inputs():
    selection = json.loads(
        (ROOT / "results/phase1/candidate_selection/qwen15b_qci1/selection.json").read_text()
    )
    rows = json.loads(
        (ROOT / "results/phase1/model_qualification/qwen15b_kaggle_20261110/mq_g1_rows.json").read_text()
    )
    protocol = json.loads(
        (ROOT / "configs/causal_candidates/qwen_1_5b_qci1_development_audit_v1.json").read_text()
    )
    return selection, rows, protocol


def test_audit_plan_caps_candidates_and_stays_within_frozen_budget() -> None:
    selection, rows, protocol = _inputs()
    supported = [f"{row['agent']}.{row['candidate_id']}" for row in selection["selected"]]
    report = {
        "overall": "PASS",
        "next_gate": "ELIGIBLE_TO_FREEZE_DEVELOPMENT_AUDIT",
        "supported_candidates": supported,
    }
    plan = build_audit_plan(report, selection, rows, protocol)
    assert len(plan["candidate_ids"]) == 8
    assert len(plan["excluded_supported_candidates"]) == 4
    assert plan["candidate_execution_count"] == 224
    assert plan["total_execution_count"] == 232
    assert plan["validation_executions"] == plan["test_executions"] == 0


def test_audit_plan_refuses_absent_support() -> None:
    selection, rows, protocol = _inputs()
    report = {
        "overall": "PASS",
        "next_gate": "STOP_NO_SUPPORTED_CANDIDATE",
        "supported_candidates": [],
    }
    with pytest.raises(ValueError, match="did not authorize"):
        build_audit_plan(report, selection, rows, protocol)
