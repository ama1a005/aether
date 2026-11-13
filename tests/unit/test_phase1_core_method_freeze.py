"""Fail-closed tests for the QCI-2 method-freeze proposal."""

from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from causal.method_freeze import load_and_validate_proposal


ROOT = Path(__file__).resolve().parents[2]
PROPOSAL = ROOT / "configs/phase1_core/qci2_method_freeze_v1.yaml"


def _write(tmp_path: Path, value: dict) -> Path:
    path = tmp_path / "proposal.yaml"
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")
    return path


def test_repository_proposal_is_valid_but_not_reviewed() -> None:
    proposal = load_and_validate_proposal(PROPOSAL, ROOT)
    assert proposal["status"] == "AWAITING_HUMAN_REVIEW"
    assert proposal["validation_case_ids"] == []
    assert proposal["test_case_ids"] == []


@pytest.mark.parametrize("field", ["case_ids", "validation_case_ids", "test_case_ids"])
def test_locked_or_audit_case_access_fails_closed(tmp_path: Path, field: str) -> None:
    proposal = yaml.safe_load(PROPOSAL.read_text(encoding="utf-8"))
    changed = deepcopy(proposal)
    changed[field] = ["v2_case_010"]
    with pytest.raises(PermissionError):
        load_and_validate_proposal(_write(tmp_path, changed), ROOT)


def test_candidate_reselection_fails_closed(tmp_path: Path) -> None:
    proposal = yaml.safe_load(PROPOSAL.read_text(encoding="utf-8"))
    proposal["candidate_graph"]["nodes"][0]["id"] = "sender.module.L21.attention_output"
    with pytest.raises(ValueError, match="candidate set differs"):
        load_and_validate_proposal(_write(tmp_path, proposal), ROOT)


def test_supported_edge_cannot_be_asserted_by_proposal(tmp_path: Path) -> None:
    proposal = yaml.safe_load(PROPOSAL.read_text(encoding="utf-8"))
    proposal["candidate_graph"]["edges"][0]["status"] = "supported"
    with pytest.raises(ValueError, match="cannot pre-label"):
        load_and_validate_proposal(_write(tmp_path, proposal), ROOT)


def test_evidence_hash_drift_fails_closed(tmp_path: Path) -> None:
    proposal = yaml.safe_load(PROPOSAL.read_text(encoding="utf-8"))
    proposal["evidence_inputs"]["qci2_audit_summary"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="hash mismatch"):
        load_and_validate_proposal(_write(tmp_path, proposal), ROOT)


def test_legacy_message_bridge_is_never_scientific_evidence() -> None:
    from causal.bridge.message_bridge import MessageBridge

    bridge = MessageBridge()
    result = bridge.to_dict()
    assert result["scientific_evidence_eligible"] is False
    assert result["evidence_class"] == "synthetic_association_scaffold"
