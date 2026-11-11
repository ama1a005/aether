"""Tests for prospective QCI-1 candidate selection."""

from __future__ import annotations

import json
import hashlib
from pathlib import Path

import pytest
import torch

from causal.qwen_candidate_selection import load_protocol, select_candidates
from causal.run_qwen_candidate_selection import _verify_discovery_artifacts


PROTOCOL = Path("configs/causal_candidates/qwen_1_5b_dcap1_intervention_v1.json")
EXECUTION_PROTOCOL = Path("configs/causal_candidates/qwen_1_5b_qci1_execution_v1_1.json")


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


def test_execution_accounting_covers_every_declared_control() -> None:
    protocol = json.loads(EXECUTION_PROTOCOL.read_text(encoding="utf-8"))
    per_candidate = sum(protocol["per_candidate_discovery_operators"].values())
    assert per_candidate * protocol["selected_candidate_count"] == protocol["expected_candidate_executions"]
    assert protocol["expected_candidate_executions"] <= protocol["maximum_discovery_intervention_executions"]
    assert protocol["development_audit"].startswith("forbidden")
    assert protocol["validation"] == protocol["test"] == "forbidden"


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


def test_discovery_hash_verification_never_requires_audit_tensor(tmp_path: Path) -> None:
    protocol = {"discovery_case_ids": ["d"], "development_audit_case_ids": ["a"]}
    records = []
    for agent in ("sender", "receiver"):
        for condition in ("clean", "attacked"):
            path = tmp_path / f"d_{agent}_{condition}.pt"
            path.write_bytes(f"{agent}-{condition}".encode())
            records.append({
                "case_id": "d", "partition": "discovery", "path": str(path),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            })
    records.append({
        "case_id": "a", "partition": "development_audit",
        "path": str(tmp_path / "missing_audit.pt"), "sha256": "unused",
    })
    verified = _verify_discovery_artifacts(tmp_path, records, protocol)
    assert len(verified) == 4
    assert all(name.startswith("d_") for name in verified)
