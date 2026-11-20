"""Model-independent integrity checks for prospective real-Qwen Agent C v1."""

from __future__ import annotations

from pathlib import Path

import yaml

from causal.remediation_freeze import frozen_text_hash_matches
from experiments.external_bundle import sha256_file


ROOT = Path(__file__).resolve().parents[2]
PROPOSAL = ROOT / "configs/experiments/agent_c_qwen_real_development_v1.yaml"
PROPOSAL_SHA256 = "9e031fb2911686702e28ec00b54299e01d428a1d2e1676050d0b3dc541d392a7"


def _proposal() -> dict:
    payload = yaml.safe_load(PROPOSAL.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_real_agent_c_proposal_identity_and_review_gate() -> None:
    """Freeze the candidate bytes while leaving approval to a human reviewer."""
    assert frozen_text_hash_matches(PROPOSAL, PROPOSAL_SHA256)
    payload = _proposal()
    assert payload["status"] == "awaiting_exact_hash_human_review"
    assert payload["locks"]["human_approval_required_before_implementation"] is True
    assert payload["locks"]["human_approval_required_before_model_access"] is True


def test_real_agent_c_inputs_are_exact_and_development_only() -> None:
    """Bind the prospective run to retained inputs and its declared 48 rows."""
    payload = _proposal()
    inputs = payload["inputs"]
    assert len(inputs["case_ids"]) == len(set(inputs["case_ids"])) == 24
    assert inputs["conditions"] == ["clean", "attacked"]
    assert inputs["expected_row_count"] == 48
    assert inputs["ground_truth_visible_to_agent_c"] is False
    for key in ("qwen_ab_rows", "qwen_ab_manifest"):
        record = inputs[key]
        assert sha256_file(ROOT / record["path"]) == record["sha256"]
    registry = inputs["case_registry"]
    assert frozen_text_hash_matches(ROOT / registry["path"], registry["canonical_lf_sha256"])


def test_real_agent_c_has_no_mock_fallback_or_success_overclaim() -> None:
    """Keep real MCP/Qwen execution distinct from deterministic support."""
    payload = _proposal()
    assert payload["mcp"]["required_tool_discovery"] is True
    assert payload["mcp"]["fallback_transport"] == "forbidden"
    assert payload["metrics"]["denominators_include_invalid_as_incorrect"] is True
    assert payload["metrics"]["performance_success_threshold"] == "none_prospectively_declared_report_estimates_only"
    assert payload["locks"]["synthetic_or_mock_rows_admissible_as_evidence"] is False
    assert payload["locks"]["deterministic_agent_c_bundle_may_satisfy_gate"] is False
    assert payload["locks"]["validation_executions"] == 0
    assert payload["locks"]["test_executions"] == 0
