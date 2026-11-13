"""Model-free unit tests for TAMAS case loader, preflight, verifier, and report assembler."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from benchmarks.nov19_tamas.case import (
    ATTACK_TYPES,
    TAMASNativeCase,
    load_tamas_dataset,
    select_predeclared_tamas_cohort,
)
from benchmarks.nov19_tamas.preflight import (
    check_tamas_dataset,
    check_tamas_framework,
    check_tamas_provider_access,
    run_tamas_preflight,
)
from benchmarks.nov19_tamas.report import assemble_tamas_summary
from benchmarks.nov19_tamas.runner import TAMASNativeRunner, TAMASTrajectoryRecord
from benchmarks.nov19_tamas.verifier import TAMASArtifactVerifier, TAMASVerificationResult


def make_dummy_tamas_data(tmp_path: Path) -> Path:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    for at in ATTACK_TYPES:
        at_dir = data_dir / at
        at_dir.mkdir()
        scenario_file = at_dir / "scenario_001.json"
        records = [
            {
                "user query": f"Query for {at}",
                "agents": [{"name": "Agent_A", "role": "assistant"}, {"name": "Agent_B", "role": "critic"}],
                "task": "collaborative decision",
            }
        ]
        scenario_file.write_text(json.dumps(records), encoding="utf-8")
    return data_dir


def test_tamas_load_dataset_all_attack_types(tmp_path):
    data_dir = make_dummy_tamas_data(tmp_path)
    cases = load_tamas_dataset(data_dir)
    assert len(cases) == 6  # 1 per attack type
    loaded_types = {c.attack_type for c in cases}
    assert loaded_types == set(ATTACK_TYPES)
    assert all(c.evaluation_origin == "tamas_native_official" for c in cases)


def test_tamas_select_cohort_balanced(tmp_path):
    data_dir = make_dummy_tamas_data(tmp_path)
    cases = load_tamas_dataset(data_dir)
    cohort = select_predeclared_tamas_cohort(cases, per_attack_count=1, seed=42)
    assert len(cohort) == 6
    assert len({c.attack_type for c in cohort}) == 6


def test_tamas_preflight_missing_credentials():
    ok, reasons, details = check_tamas_provider_access(provider="openai", api_key_env_var="NONEXISTENT_KEY_FOR_TEST")
    assert not ok
    assert any("requires credentials" in r for r in reasons)


def test_tamas_preflight_unexpected_framework():
    ok, reasons, _ = check_tamas_framework(required_framework="unsupported_framework_xyz")
    assert not ok
    assert any("Unsupported multi-agent framework" in r for r in reasons)


def test_tamas_preflight_missing_dataset_directory(tmp_path):
    ok, reasons, _ = check_tamas_dataset(tmp_path / "absent_data")
    assert not ok
    assert any("not found" in r for r in reasons)


def test_tamas_verifier_detects_duplicate_ids(tmp_path):
    res_dir = tmp_path / "results"
    res_dir.mkdir()
    rows = [
        {"case_id": "Byzantine:s1:000", "attack_type": "Byzantine", "is_valid": True, "evaluation_method": "deterministic"},
        {"case_id": "Byzantine:s1:000", "attack_type": "Byzantine", "is_valid": True, "evaluation_method": "deterministic"},
    ]
    (res_dir / "trajectories.json").write_text(json.dumps(rows), encoding="utf-8")

    verifier = TAMASArtifactVerifier(res_dir)
    res = verifier.verify()
    assert not res.passed
    assert any("Duplicate case_id" in r for r in res.reasons)


def test_tamas_verifier_detects_missing_judge_identity(tmp_path):
    res_dir = tmp_path / "results"
    res_dir.mkdir()
    rows = [
        {
            "case_id": "Byzantine:s1:000",
            "attack_type": "Byzantine",
            "is_valid": True,
            "evaluation_method": "llm_judge",
            "judge_metadata": {},  # Missing judge_model
        }
    ]
    (res_dir / "trajectories.json").write_text(json.dumps(rows), encoding="utf-8")

    verifier = TAMASArtifactVerifier(res_dir)
    res = verifier.verify()
    assert not res.passed
    assert any("without declaring judge_model" in r for r in res.reasons)


def test_tamas_verifier_retains_errors_and_outages(tmp_path):
    res_dir = tmp_path / "results"
    res_dir.mkdir()
    rows = [
        {"case_id": "Byzantine:s1:000", "attack_type": "Byzantine", "is_valid": True, "is_attack_success": True, "evaluation_method": "deterministic"},
        {"case_id": "Colluding:s1:000", "attack_type": "Colluding", "is_valid": False, "error_type": "network_timeout", "evaluation_method": "deterministic"},
    ]
    (res_dir / "trajectories.json").write_text(json.dumps(rows), encoding="utf-8")

    verifier = TAMASArtifactVerifier(res_dir)
    res = verifier.verify()
    assert res.passed
    assert res.metrics["total_cases"] == 2
    assert res.metrics["total_invalid"] == 1
    assert res.metrics["total_errors"] == 1
    assert res.metrics["total_success"] == 1


def test_tamas_verifier_rejects_evidence_class_inflation(tmp_path):
    res_dir = tmp_path / "smoke_dir"
    res_dir.mkdir()
    rows = [{"case_id": "Byzantine:s1:000", "attack_type": "Byzantine", "is_valid": True, "evaluation_method": "deterministic"}]
    (res_dir / "trajectories.json").write_text(json.dumps(rows), encoding="utf-8")
    (res_dir / "summary.json").write_text(json.dumps({"result_state": "SMOKE", "official_protocol": True}), encoding="utf-8")

    verifier = TAMASArtifactVerifier(res_dir)
    res = verifier.verify()
    assert not res.passed
    assert any("Evidence class violation" in r for r in res.reasons)


def test_tamas_report_assembler_blocked_and_pilot():
    ver_res = TAMASVerificationResult(
        passed=True,
        reasons=(),
        metrics={"total_cases": 6, "total_success": 2, "total_invalid": 0, "overall_asr": 0.33, "by_attack": {}},
        artifact_hashes={"trajectories.json": "hash123"},
    )
    # Pilot run
    pilot_summary = assemble_tamas_summary(ver_res, is_pilot=True)
    assert pilot_summary["is_pilot"] is True
    assert pilot_summary["evidence_class"] == "official_native_subset"
    assert pilot_summary["status"] == "PASSED"

    # Blocked run
    blocked_summary = assemble_tamas_summary(
        ver_res,
        execution_blocked_reasons=["AutoGen framework not installed in standard environment"],
    )
    assert blocked_summary["official_protocol"] is False
    assert blocked_summary["status"] == "BLOCKED"
    assert blocked_summary["overall"] == "BLOCKED"
