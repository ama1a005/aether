"""Model-free checks for the qualified Qwen instrumentation-acceptance gate."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from instrumentation.run_qwen_instrumentation_acceptance import (
    _load_config,
    _write_failure_manifest,
    preflight,
    verify_qualification_bundle,
)


def test_ingested_qwen_qualification_is_complete_and_hash_verified() -> None:
    """Require the exact successful development-only run before instrumentation."""
    config = _load_config()
    summary, rows = verify_qualification_bundle(config)
    assert summary["decision"] == "QUALIFIED_FOR_SEPARATE_INSTRUMENTATION_REVIEW"
    assert summary["mq_g1"]["overall"] == "PASS"
    assert summary["mq_g2"]["overall"] == "PASS"
    assert summary["validation_executions"] == summary["test_executions"] == 0
    assert [row["case_id"] for row in rows] == config["selected_case_ids"]
    assert {row["direction"] for row in rows} == {"A_TO_B", "B_TO_A"}


def test_instrumentation_gate_is_prospective_bounded_and_cpu_exact() -> None:
    """Keep acceptance separate from discovery and locked-split evaluation."""
    config = _load_config()
    assert config["gate_version"] == "IA-G1.0"
    assert config["execution"] == {
        "device": "cpu",
        "dtype": "float32",
        "quantized": False,
        "offload": False,
        "attention_implementation": "eager",
        "seed": 42,
    }
    assert config["split_access_policy"]["validation"] == "forbidden"
    assert config["split_access_policy"]["test"] == "forbidden"
    assert len(config["selected_case_ids"]) == 4
    assert "No component ranking" in config["claim_boundary"]


def test_preflight_and_failure_records_contain_required_provenance(tmp_path: Path) -> None:
    """Retain complete metadata before access and after any explicit failure."""
    result = preflight(tmp_path, tmp_path)
    assert result["model_accessed"] is False
    assert result["git_commit"]
    assert result["model_revision"]
    assert result["random_seeds"] == [42]
    assert result["python_env_hash"]
    _write_failure_manifest(tmp_path, RuntimeError("fixture failure"))
    failure = json.loads((tmp_path / "failure_manifest.json").read_text(encoding="utf-8"))
    assert failure["failure"] == {
        "exception_type": "RuntimeError", "message": "fixture failure"
    }
    assert failure["dataset_manifest_hashes"]
    assert failure["artifact_paths"]


def test_qualification_hash_mismatch_fails_closed() -> None:
    """Reject a qualification prerequisite whose frozen digest is altered."""
    config = _load_config()
    config["qualification_summary_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="qualified summary hash differs"):
        verify_qualification_bundle(config)
