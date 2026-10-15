"""Unit tests for the balanced causal substrate V2 contract."""

from __future__ import annotations

import pytest
import torch
import json
from pathlib import Path

from causal.v2_classification import classify_candidate
from paired_trace.balanced_v2 import (
    build_control_mappings, build_registry, case_normalized_margin, require_v2_development,
)
from paired_trace.run_balanced_v2_baseline import _select_cases
from experiments.manifest import sha256_file


def test_v2_registry_is_deterministic_balanced_and_diverse() -> None:
    first = build_registry()
    assert first == build_registry()
    assert {split: len(ids) for split, ids in first["splits"].items()} == {
        "development": 24, "validation": 8, "test": 8,
    }
    for split, expected in (("development", 12), ("validation", 4), ("test", 4)):
        cases = [case for case in first["cases"] if case["split"] == split]
        assert sum(case["ground_truth_code"] == "A" for case in cases) == expected
        assert sum(case["ground_truth_code"] == "B" for case in cases) == expected
        assert len({case["template_family"] for case in cases}) >= 8


def test_v2_attack_directions_are_symmetric_and_locked() -> None:
    registry = build_registry()
    development = [case for case in registry["cases"] if case["split"] == "development"]
    assert {case["attack_direction"] for case in development} == {"A_TO_B", "B_TO_A"}
    assert all(case["ground_truth_code"] != case["adversarial_code"] for case in development)
    require_v2_development(development[0])
    with pytest.raises(PermissionError, match="locked"):
        require_v2_development(next(case for case in registry["cases"] if case["split"] == "validation"))
    with pytest.raises(PermissionError, match="locked"):
        _select_cases(registry, "full", "validation")
    with pytest.raises(PermissionError, match="locked"):
        _select_cases(registry, "full", "test")


def test_v2_shuffle_mappings_have_correct_labels_and_no_self_maps() -> None:
    registry = build_registry()
    mappings = build_control_mappings(registry)
    by_id = {case["case_id"]: case for case in registry["cases"]}
    for source, target in mappings["same_label"].items():
        assert source != target
        assert by_id[source]["split"] == by_id[target]["split"]
        assert by_id[source]["ground_truth_code"] == by_id[target]["ground_truth_code"]
    for source, target in mappings["opposite_label"].items():
        assert source != target
        assert by_id[source]["split"] == by_id[target]["split"]
        assert by_id[source]["ground_truth_code"] != by_id[target]["ground_truth_code"]


def test_case_normalized_score_has_consistent_sign() -> None:
    logits = torch.tensor([[[5.0, 1.0]], [[1.0, 5.0]]])
    scores, raw_a, raw_b = case_normalized_margin(logits, {"A": 0, "B": 1}, ["A", "B"])
    assert scores.tolist() == [4.0, 4.0]
    assert raw_a.tolist() == [5.0, 1.0] and raw_b.tolist() == [1.0, 5.0]


def _directions(**overrides: float) -> dict[str, dict[str, float]]:
    base = dict(
        paired_rescue=0.8, paired_induction=0.8, same_label_rescue=0.8,
        opposite_label_rescue=0.0, irrelevant_rescue=0.0, matched_control_rescue=0.0,
    )
    base.update(overrides)
    return {direction: dict(base) for direction in ("A_TO_B", "B_TO_A")}


def test_candidate_class_logic_and_generic_overwrite_detection() -> None:
    assert classify_candidate(_directions()) == "LABEL_LEVEL"
    assert classify_candidate(_directions(same_label_rescue=0.2)) == "CASE_SPECIFIC"
    assert classify_candidate(_directions(opposite_label_rescue=0.75)) == "GENERIC_OVERWRITE"
    assert classify_candidate(_directions(paired_rescue=0.1, paired_induction=0.1)) == "UNSUPPORTED"
    assert classify_candidate({"A_TO_B": _directions()["A_TO_B"]}) == "INSUFFICIENT"


def test_constant_a_bias_cannot_qualify_without_b_direction() -> None:
    rows = _directions()
    rows["B_TO_A"]["paired_induction"] = 0.0
    assert classify_candidate(rows) == "BROAD_CAUSAL_RESPONDER"


def test_v2_baseline_result_provenance_and_manifest_hashes() -> None:
    root = Path("results/phase1/balanced_v2/full_v2_1")
    summary = json.loads((root / "summary.json").read_text(encoding="utf-8"))
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    assert summary["executed_split"] == "development"
    assert summary["validation_test_accessed"] is False
    assert len(manifest["subset_ids"]) == 24
    assert all(case_id.startswith("v2_case_") for case_id in manifest["subset_ids"])
    for artifact, expected in manifest["artifacts"].items():
        assert sha256_file(Path(artifact)) == expected


def test_v2_1_freeze_manifest_matches_precausal_files() -> None:
    path = Path("data/causal_v2/freeze_manifest_v2_1.json")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    assert manifest["scope"] == "development_only"
    assert manifest["validation_test_accessed"] is False
    for artifact, expected in manifest["files"].items():
        assert sha256_file(Path(artifact)) == expected


def test_v2_pivot_evidence_is_development_only_and_hash_valid() -> None:
    root = Path("results/phase1/balanced_v2")
    manifest = json.loads((root / "pivot_manifest.json").read_text(encoding="utf-8"))
    evidence = json.loads((root / "revised_dcmg_evidence.json").read_text(encoding="utf-8"))
    assert manifest["split"] == "development" and manifest["validation_test_accessed"] is False
    assert {edge["status"] for edge in evidence} == {"supported", "insufficient"}
    assert all(edge["split"] == "development" for edge in evidence)
    for artifact, expected in manifest["artifacts"].items():
        assert sha256_file(Path(artifact)) == expected
