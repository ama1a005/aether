"""Model-free unit tests for BFCL preflight, runner, verifier, and report assembler."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import pytest

from benchmarks.nov19_bfcl.preflight import (
    ADAPTER_REGISTRY_NAME,
    PHASE1_CATEGORIES,
    PINNED_MODEL_ID,
    PINNED_MODEL_REVISION,
    PINNED_PACKAGE,
    PINNED_PACKAGE_VERSION,
    check_backend_and_hardware,
    check_categories,
    check_package,
    check_snapshot_manifest,
    run_bfcl_preflight,
)
from benchmarks.nov19_bfcl.report import assemble_bfcl_summary
from benchmarks.nov19_bfcl.runner import BFCLRunner
from benchmarks.nov19_bfcl.verifier import BFCLArtifactVerifier, VerificationResult


def test_package_check_wrong_version():
    ok, reasons, details = check_package(
        package_name=PINNED_PACKAGE,
        expected_version="999.999.999",
    )
    assert not ok
    assert any("not installed" in r or "version mismatch" in r for r in reasons)


def test_package_check_wheel_hash_mismatch(tmp_path):
    wheel = tmp_path / "test.whl"
    wheel.write_bytes(b"dummy-wheel-bytes")
    ok, reasons, details = check_package(
        package_name="pytest",
        expected_version="9.2.0",
        wheel_path=wheel,
        expected_wheel_sha256="0000000000000000000000000000000000000000000000000000000000000000",
    )
    assert not ok
    assert any("Wheel hash mismatch" in r for r in reasons)


def test_backend_hardware_rejects_invalid_backend():
    ok, reasons, details = check_backend_and_hardware(backend="unsupported_engine")
    assert not ok
    assert any("Unsupported backend" in r for r in reasons)


def test_categories_rejects_empty_or_invalid():
    ok, reasons, _ = check_categories([])
    assert not ok
    assert any("empty" in r for r in reasons)

    ok, reasons, _ = check_categories(["invalid_category_xyz"])
    assert not ok
    assert any("Unknown BFCL categories" in r for r in reasons)


def test_snapshot_manifest_absent(tmp_path):
    ok, reasons, _ = check_snapshot_manifest(tmp_path / "absent.json")
    assert not ok
    assert any("not found" in r for r in reasons)


def test_snapshot_manifest_wrong_revision(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({
        "model_id": PINNED_MODEL_ID,
        "resolved_revision": "wrong_revision_sha",
        "snapshot_path": str(tmp_path),
        "files": [],
    }))
    ok, reasons, _ = check_snapshot_manifest(manifest, expected_revision=PINNED_MODEL_REVISION)
    assert not ok
    assert any("Revision mismatch" in r for r in reasons)


def test_snapshot_manifest_malformed_json(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text("not json content")
    ok, reasons, _ = check_snapshot_manifest(manifest)
    assert not ok
    assert any("Failed to parse" in r for r in reasons)


def test_snapshot_manifest_file_tampering(tmp_path):
    snap_dir = tmp_path / PINNED_MODEL_REVISION
    snap_dir.mkdir()
    target = snap_dir / "config.json"
    target.write_bytes(b"correct content")

    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({
        "model_id": PINNED_MODEL_ID,
        "resolved_revision": PINNED_MODEL_REVISION,
        "snapshot_path": str(snap_dir),
        "files": [{"path": "config.json", "size": len(b"correct content"), "sha256": sha256(b"correct content").hexdigest()}],
    }))

    ok, reasons, _ = check_snapshot_manifest(manifest, verify_file_hashes=True)
    assert ok

    # Tamper with the file
    target.write_bytes(b"tampered content")
    ok, reasons, _ = check_snapshot_manifest(manifest, verify_file_hashes=True)
    assert not ok
    assert any("mismatch" in r for r in reasons)


def test_verifier_rejects_missing_directory(tmp_path):
    verifier = BFCLArtifactVerifier(tmp_path / "nonexistent")
    res = verifier.verify()
    assert not res.passed
    assert any("does not exist" in r for r in res.reasons)


def test_verifier_rejects_partial_categories(tmp_path):
    res_dir = tmp_path / "results"
    res_dir.mkdir()
    # Create output for simple only
    simple_file = res_dir / "simple.json"
    simple_file.write_text(json.dumps([{"id": "s1", "success": True, "valid": True}]))

    verifier = BFCLArtifactVerifier(res_dir, expected_categories=["simple", "multiple"])
    res = verifier.verify()
    assert not res.passed
    assert any("Missing evaluator output for category: multiple" in r for r in res.reasons)


def test_verifier_detects_duplicate_task_ids(tmp_path):
    res_dir = tmp_path / "results"
    res_dir.mkdir()
    file_1 = res_dir / "simple.json"
    file_1.write_text(json.dumps([
        {"id": "duplicate_id_01", "success": True, "valid": True},
        {"id": "duplicate_id_01", "success": True, "valid": True},
    ]))
    verifier = BFCLArtifactVerifier(res_dir, expected_categories=["simple"])
    res = verifier.verify()
    assert not res.passed
    assert any("Duplicate task ID duplicate_id_01" in r for r in res.reasons)


def test_verifier_retains_errors_in_denominator(tmp_path):
    res_dir = tmp_path / "results"
    res_dir.mkdir()
    simple_file = res_dir / "simple.json"
    simple_file.write_text(json.dumps([
        {"id": "s1", "success": True, "valid": True},
        {"id": "s2", "success": False, "valid": False, "error": "timeout"},
    ]))
    verifier = BFCLArtifactVerifier(res_dir, expected_categories=["simple"])
    res = verifier.verify()
    assert res.passed
    assert res.metrics["total_eligible"] == 2
    assert res.metrics["total_errors"] == 1
    assert res.metrics["total_success"] == 1
    assert res.metrics["overall_accuracy"] == 0.5


def test_report_fails_closed_without_unwarranted_official_evaluator(tmp_path):
    # Verification failed
    failed_res = VerificationResult(
        passed=False,
        reasons=("Missing categories",),
        metrics={},
        artifact_hashes={},
    )
    summary = assemble_bfcl_summary(failed_res)
    assert summary["official_evaluator"] is False
    assert summary["official_evaluator_executed"] is False
    assert summary["status"] == "FAILED"
    assert summary["overall"] == "FAIL"

    # Blocked state
    blocked_summary = assemble_bfcl_summary(
        failed_res,
        execution_blocked_reasons=["CUDA GPU unavailable on laptop 2"],
    )
    assert blocked_summary["official_evaluator"] is False
    assert blocked_summary["official_evaluator_executed"] is False
    assert blocked_summary["status"] == "BLOCKED"
    assert blocked_summary["overall"] == "BLOCKED"
    assert any("CUDA GPU unavailable" in l for l in blocked_summary["limitations"])


def test_runner_dry_run_generates_diagnostics(tmp_path):
    snap_manifest = tmp_path / "manifest.json"
    snap_manifest.write_text(json.dumps({
        "model_id": PINNED_MODEL_ID,
        "resolved_revision": PINNED_MODEL_REVISION,
        "snapshot_path": str(tmp_path),
        "files": [],
    }))
    runner = BFCLRunner(
        snapshot_manifest=snap_manifest,
        output_dir=tmp_path / "output",
    )
    dry = runner.dry_run()
    assert "preflight" in dry
    assert "output_dir" in dry
    # Preflight should fail because CUDA and bfcl_eval are not present in this test env
    assert not dry["preflight"]["passed"]
