"""Tests for prospective QCI-1 candidate selection."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import torch

from causal.qwen_candidate_selection import load_protocol, select_candidates


PROTOCOL = Path("configs/causal_candidates/qwen_1_5b_dcap1_intervention_v1.json")


def _artifact(scale: float) -> dict[str, torch.Tensor]:
    heads = torch.ones((1, 12, 2))
    heads[:, 3, :] *= scale
    return {
        "module.L0.attention_output": torch.tensor([[scale, 1.0]]),
        "module.L0.mlp_output": torch.tensor([[1.0, scale]]),
        "head.L0.pre_o_proj_heads": heads,
    }


def test_protocol_is_frozen_and_keeps_locked_splits_closed() -> None:
    protocol = load_protocol(PROTOCOL)
    assert len(protocol["discovery_case_ids"]) == 16
    assert len(protocol["development_audit_case_ids"]) == 4
    assert not set(protocol["discovery_case_ids"]) & set(protocol["development_audit_case_ids"])
    assert protocol["split_access_policy"]["validation"] == "forbidden"
    assert protocol["split_access_policy"]["test"] == "forbidden"
    assert protocol["budget"]["maximum_selected_internal_candidates"] == 12


def test_selection_is_discovery_only_deterministic_and_expands_heads(tmp_path: Path) -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    protocol["discovery_case_ids"] = ["a", "b"]
    protocol["development_audit_case_ids"] = ["locked"]
    protocol["selection"]["top_k_modules_per_agent"] = 1
    protocol["selection"]["top_k_heads_per_agent"] = 1
    rows = [{"case_id": "a", "direction": "A_TO_B"}, {"case_id": "b", "direction": "B_TO_A"}]
    for case_id in ("a", "b"):
        for agent in ("sender", "receiver"):
            torch.save(_artifact(1.0), tmp_path / f"{case_id}_{agent}_clean.pt")
            torch.save(_artifact(4.0), tmp_path / f"{case_id}_{agent}_attacked.pt")
    first = select_candidates(tmp_path, rows, protocol)
    second = select_candidates(tmp_path, rows, protocol)
    assert first == second
    assert first["development_audit_accessed"] is False
    assert first["candidate_universe_count"] == 28
    assert first["selected_count"] == 4
    assert any(".H3." in item["candidate_id"] for item in first["selected"])


def test_selection_fails_closed_for_missing_discovery_pair(tmp_path: Path) -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    protocol["discovery_case_ids"] = ["a", "b"]
    protocol["development_audit_case_ids"] = []
    rows = [{"case_id": "a", "direction": "A_TO_B"}, {"case_id": "b", "direction": "B_TO_A"}]
    with pytest.raises(FileNotFoundError, match="missing discovery activation pair"):
        select_candidates(tmp_path, rows, protocol)
