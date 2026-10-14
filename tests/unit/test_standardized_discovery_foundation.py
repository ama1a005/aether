"""Tests for standardized benchmark adapters and development causal discovery."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from benchmarks.mcptox import deterministic_smoke_subset, load_official_cases, summarize_official_labels
from benchmarks.tamas import ATTACK_TYPES, load_tamas_cases
from causal.development_baselines import QueryBudget, clean_utility, deterministic_matched_controls, trace_level_replay
from causal.evidence import CausalEdgeEvidence
from causal.run_specificity_hardening import (
    _evaluate_candidate,
    _induction,
    _recovery,
    _sample_controls,
)
from experiments.manifest import sha256_file
from instrumentation.model_adapter import ComponentSite
import torch


def test_mcptox_loader_preserves_poisoned_metadata_and_origin(tmp_path) -> None:
    path = tmp_path / "pure_tool.json"
    path.write_text(json.dumps([{"Server_1": {"server_name": "Server", "tool_name": "poison", "query": "q", "tool_content": "malicious metadata", "security risk": "Risk", "paradigm": "Template-1", "tool_address": "def_tool/1.py"}}]), encoding="utf-8")
    cases = load_official_cases(path, verify_pinned_hash=False)
    assert cases[0].poisoned_description == "malicious metadata"
    assert cases[0].evaluation_origin == "mcptox_official_compatible"


def test_mcptox_pinned_identity_fails_closed(tmp_path) -> None:
    path = tmp_path / "pure_tool.json"
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="pinned release"):
        load_official_cases(path)


def test_mcptox_subset_and_official_label_scoring_are_deterministic() -> None:
    from benchmarks.mcptox import MCPToxCase
    cases = [MCPToxCase(f"z_{i}", "s", "t", "q", "p", "r", "Template-1", "a") for i in range(30, 0, -1)]
    assert [case.case_id for case in deterministic_smoke_subset(cases, 3)] == ["z_1", "z_10", "z_11"]
    result = summarize_official_labels(["Success", "Failure-Ignored", "None"])
    assert result["N_scored"] == 2 and result["attack_success_rate"] == 0.5


def test_result_origins_remain_separate() -> None:
    origins = {"mcptox_official_compatible", "mcptox_aether_transformed", "aether_positive_control"}
    assert len(origins) == 3


def test_tamas_adapter_preserves_native_records(tmp_path) -> None:
    for attack in ATTACK_TYPES:
        directory = tmp_path / attack
        directory.mkdir()
        (directory / f"education_{attack}.json").write_text(json.dumps([{"agents": [], "user query": "q"}]), encoding="utf-8")
    cases = load_tamas_cases(tmp_path)
    assert len(cases) == 6 and {case.attack_type for case in cases} == set(ATTACK_TYPES)


def test_matched_controls_and_query_budget_are_reproducible() -> None:
    candidates = [f"L{i}.mlp_output" for i in range(6)]
    first = deterministic_matched_controls(candidates, [candidates[0]], [11, 22, 33])
    assert first == deterministic_matched_controls(candidates, [candidates[0]], [11, 22, 33])
    budget = QueryBudget(sender_forwards=2, sender_generations=3, receiver_forwards=4)
    assert budget.total == 9


def test_supported_edge_requires_intervention_evidence() -> None:
    common = dict(edge_id="e", source_node="s", target_node="t", source_type="internal", target_type="message", intervention_operator="patch", pair_ids=("pair_000",), n_attempted=1, n_eligible=1, effect_values=(1.0,), summary_effect=1.0, effect_direction="toward_clean", control_effect=0.0, artifact_refs=("a",), manifest_refs=("m",), split="development")
    with pytest.raises(ValueError, match="intervention"):
        CausalEdgeEvidence(evidence_type="association", status="supported", **common)
    assert CausalEdgeEvidence(evidence_type="activation_intervention", status="supported", **common).status == "supported"


def test_candidate_discovery_rejects_locked_split() -> None:
    with pytest.raises(PermissionError, match="development-only"):
        CausalEdgeEvidence("e", "s", "t", "x", "y", "activation_intervention", "patch", ("p",), 1, 1, (1.0,), 1.0, "toward_clean", 0.0, ("a",), ("m",), "test", "supported")


def test_trace_replay_and_clean_utility() -> None:
    assert trace_level_replay("clean", "attack", True) == "clean"
    result = clean_utility(["A", "A"], ["A", "B"], [2.0, 1.0], [1.5, -0.5], 0, 0.2)
    assert result["clean_accuracy_before"] == 1.0
    assert result["clean_accuracy_after"] == 0.5


def test_frozen_candidate_registry_identity() -> None:
    path = Path("configs/causal_candidates/qwen2_5_0_5b_phase1_coarse.json")
    registry = json.loads(path.read_text(encoding="utf-8"))
    assert registry["frozen_before_scan"] and registry["scope"] == "development_only"
    assert registry["layers"] == [0, 5, 9, 14, 18, 23]
    assert sha256_file(path) == "aa96328c63afd46ba6a004f9091e6675cde666fb9f82918e5a332d19554cee11"


def test_completed_causal_scan_and_fixed_receiver_messages() -> None:
    root = Path("results/phase1/causal_discovery")
    sender = json.loads((root / "sender_scan.json").read_text(encoding="utf-8"))
    receiver = json.loads((root / "receiver_scan.json").read_text(encoding="utf-8"))
    evidence = json.loads((root / "dcmg_evidence.json").read_text(encoding="utf-8"))
    assert len(sender) == len(receiver) == 18
    assert all(row["fixed_message_sha256"] == receiver[0]["fixed_message_sha256"] for row in receiver)
    assert all(edge["evidence_type"] == "activation_intervention" for edge in evidence if edge["status"] == "supported")


def test_completed_discovery_manifest_hashes() -> None:
    root = Path("results/phase1/causal_discovery")
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["split"] == "development"
    for artifact, expected in manifest["artifacts"].items():
        assert sha256_file(Path(artifact)) == expected


def test_specificity_metrics_have_expected_bidirectional_sign() -> None:
    clean = torch.tensor([2.0, 4.0])
    attacked = torch.tensor([-2.0, 0.0])
    assert _recovery(clean, attacked, clean) == [1.0, 1.0]
    assert _induction(clean, attacked, attacked) == [1.0, 1.0]


def test_specificity_controls_are_deterministic_and_retain_strong_control() -> None:
    config = json.loads(Path("configs/causal_candidates/qwen2_5_0_5b_specificity_hardening.json").read_text(encoding="utf-8"))
    sites = [
        ComponentSite(f"L{layer}.{kind}", layer, kind, "test")
        for layer in (0, 5, 9, 14, 18, 23)
        for kind in ("block_output", "attention_output")
    ]
    first = _sample_controls(config, sites)
    assert first == _sample_controls(config, sites)
    assert len(first) == 12
    assert first[0] == {"seed": 101, "role": "sender", "site": "L23.block_output", "retained_prior_strong_control": True}


def test_frozen_specificity_thresholds_control_support_transition() -> None:
    config = json.loads(Path("configs/causal_candidates/qwen2_5_0_5b_specificity_hardening.json").read_text(encoding="utf-8"))
    row = {
        "candidate_id": "sender.L14.block_output",
        "component_type": "block_output",
        "rescue": {"median": 1.0, "values": [1.0] * 16},
        "induction": {"median": 1.0, "values": [1.0] * 16},
        "shuffled_rescue": {"median": 0.0, "values": [0.0] * 16},
    }
    controls = [{"role": "sender", "component_type": "block_output", "rescue": {"median": 0.0}}]
    positions = {"sender": {"irrelevant": {"median": 0.0}}}
    assert _evaluate_candidate(row, "sender", controls, positions, config)["status"] == "supported"
    row["shuffled_rescue"]["median"] = 1.0
    rejected = _evaluate_candidate(row, "sender", controls, positions, config)
    assert rejected["status"] == "rejected"
    assert rejected["reasons"] == ["shuffled_separation"]


def test_specificity_artifacts_keep_receiver_messages_fixed_and_hashes_valid() -> None:
    root = Path("results/phase1/causal_specificity")
    results = json.loads((root / "hardening_results.json").read_text(encoding="utf-8"))
    assert all(
        row["fixed_attacked_message_sha256"] == results["receiver"][0]["fixed_attacked_message_sha256"]
        and row["fixed_clean_message_sha256"] == results["receiver"][0]["fixed_clean_message_sha256"]
        for row in results["receiver"]
    )
    assert all(pair != source for row in results["sender"] + results["receiver"] for pair, source in row["shuffled_mapping"].items())
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["split"] == "development"
    for artifact, expected in manifest["artifacts"].items():
        assert sha256_file(Path(artifact)) == expected
