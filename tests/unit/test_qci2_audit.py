"""Tests for the prospectively frozen QCI-2 development-audit plan."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from causal.qci_audit import build_audit_plan


ROOT = Path(__file__).resolve().parents[2]


def _inputs():
    selection = json.loads((ROOT / "results/phase1/candidate_selection/qwen15b_qci1/selection.json").read_text())
    rows = json.loads((ROOT / "results/phase1/model_qualification/qwen15b_kaggle_20261110/mq_g1_rows.json").read_text())
    protocol = json.loads((ROOT / "configs/causal_candidates/qwen_1_5b_qci2_development_audit_v1.json").read_text())
    return selection, rows, protocol


def test_qci2_audit_retains_all_supported_candidates_and_locked_cases() -> None:
    selection, rows, protocol = _inputs()
    supported = [f"{row['agent']}.{row['candidate_id']}" for row in selection["selected"]]
    plan = build_audit_plan({
        "overall": "PASS",
        "next_gate": "ELIGIBLE_TO_FREEZE_QCI2_DEVELOPMENT_AUDIT",
        "supported_candidates": supported,
    }, selection, rows, protocol)
    assert len(plan["candidate_ids"]) == 12
    assert plan["excluded_supported_candidates"] == []
    assert plan["case_ids"] == ["v2_case_010", "v2_case_011", "v2_case_022", "v2_case_023"]
    assert plan["candidate_execution_count"] == 480
    assert plan["total_execution_count"] == 488
    assert plan["validation_executions"] == plan["test_executions"] == 0


def test_qci2_audit_refuses_wrong_or_empty_discovery_gate() -> None:
    selection, rows, protocol = _inputs()
    with pytest.raises(ValueError, match="did not authorize"):
        build_audit_plan({"overall": "PASS", "next_gate": "STOP_DECISION_SEMANTIC_CLAIM", "supported_candidates": []}, selection, rows, protocol)
