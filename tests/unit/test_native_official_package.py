"""Model-free tests for official benchmark execution packages."""

from pathlib import Path
from datetime import datetime, timezone
import json
import subprocess
import sys

import pytest

from benchmarks import run_native_official


def test_bfcl_config_hash_accepts_git_newline_conversion_only(tmp_path) -> None:
    canonical = run_native_official.DEFAULT_CONFIG.read_bytes()
    lf = canonical.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    converted = tmp_path / "phase1_external.yaml"
    converted.write_bytes(lf)
    original = run_native_official.DEFAULT_CONFIG
    run_native_official.DEFAULT_CONFIG = converted
    try:
        loaded = run_native_official._load_config(converted, "bfcl")
        assert loaded["bfcl"]["package"] == "bfcl_eval"
        converted.write_bytes(lf + b"\n# scientific drift\n")
        with pytest.raises(ValueError, match="hash differs"):
            run_native_official._load_config(converted, "bfcl")
    finally:
        run_native_official.DEFAULT_CONFIG = original
from benchmarks.run_native_official import build_plan
from benchmarks.nov19_bfcl.preflight import (
    ADAPTER_REGISTRY_NAME,
    PHASE1_CATEGORIES,
    PINNED_CUDA_VERSION,
    PINNED_MODEL_ID,
    PINNED_MODEL_REVISION,
    PINNED_PACKAGE_VERSION,
    PINNED_BACKEND_VERSION,
    PINNED_TORCH_VERSION,
    PINNED_WHEEL_SHA256,
    BFCLPreflightResult,
)
from experiments.external_bundle import verify_bundle
from scripts.verify_bfcl_bundle import verify as verify_bfcl_bundle


CONFIG = Path("configs/benchmarks/phase1_external.yaml")


def _fixture_metadata(output: Path) -> dict:
    """Return test-only pinned metadata; never persisted outside pytest temp dirs."""
    return {
        "experiment_id": "P0_target_20261119_bfcl_fixture_0",
        "run_id": "bfcl-fixture",
        "utc_timestamp": datetime.now(timezone.utc).isoformat(),
        "git_commit": "fixture-commit",
        "uncommitted_diff": False,
        "dataset_manifest_hashes": {"fixture": "test-only"},
        "model_id": PINNED_MODEL_ID,
        "model_revision": PINNED_MODEL_REVISION,
        "tokenizer_revision": PINNED_MODEL_REVISION,
        "prompt_versions": {"bfcl_adapter": ADAPTER_REGISTRY_NAME},
        "random_seeds": [0],
        "hardware": "pytest fixture; no model or GPU execution",
        "python_env_hash": "test-only",
        "command_line": ["pytest", "test-only-fixture"],
        "config_file": str(CONFIG.resolve()),
        "raw_output_path": str((output / "official_raw").resolve()),
        "evidence_kind": "bfcl_official",
        "validation_executions": 0,
        "test_executions": 0,
        "package_wheel_sha256": PINNED_WHEEL_SHA256,
        "protocol_label": "official_evaluator_with_disclosed_aether_model_adapter",
        "inference_backend": "vllm",
        "inference_backend_version": PINNED_BACKEND_VERSION,
        "torch_version": f"{PINNED_TORCH_VERSION}+cu130",
        "cuda_runtime_version": PINNED_CUDA_VERSION,
    }


def _install_bfcl_run_fixtures(monkeypatch, tmp_path, *, preflight, execute):
    """Isolate runner orchestration from approval, model, GPU, and native execution."""
    snapshot = tmp_path / "snapshot-manifest.json"
    snapshot.write_text("{}", encoding="utf-8")
    wheel = tmp_path / "bfcl.whl"
    wheel.write_bytes(b"test-only fixture; not an official wheel")
    monkeypatch.setattr(run_native_official, "_command", lambda command: "")
    monkeypatch.setattr(
        "experiments.external_bundle.verify_protocol_approval",
        lambda proposal, decision: {"approved": True, "reviewer": "test fixture"},
    )
    monkeypatch.setattr(
        run_native_official,
        "_make_bfcl_metadata",
        lambda config_path, snapshot_path, wheel_path, output: _fixture_metadata(output),
    )
    monkeypatch.setattr(run_native_official, "run_bfcl_preflight", lambda **kwargs: preflight)
    monkeypatch.setattr(run_native_official, "execute_native_plan", execute)
    return snapshot, wheel


def test_bfcl_and_agentdojo_packages_use_pinned_official_interfaces(tmp_path) -> None:
    snapshot = tmp_path / "snapshot.json"
    snapshot.write_text("{}", encoding="utf-8")
    bfcl = build_plan("bfcl", CONFIG, tmp_path / "bfcl", snapshot)
    dojo = build_plan("agentdojo", CONFIG, tmp_path / "dojo", None)
    assert bfcl.package == "bfcl_eval" and bfcl.package_version == "2026.3.23"
    assert "989aa7980e4cf806f80c7fef2b1adb7bc71aa306" in bfcl.commands[0]
    assert dojo.package == "agentdojo" and dojo.package_version == "0.1.35"
    assert "v1.2.2" in dojo.commands[0]


def test_official_package_rejects_unknown_benchmark_or_missing_snapshot(tmp_path) -> None:
    with pytest.raises(FileNotFoundError):
        build_plan("bfcl", CONFIG, tmp_path, None)
    with pytest.raises(ValueError, match="unsupported"):
        build_plan("other", CONFIG, tmp_path, None)


def test_bfcl_missing_human_approval_fails_before_snapshot_or_model_access(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(run_native_official, "_command", lambda command: "")
    output = tmp_path / "bfcl"
    with pytest.raises(PermissionError, match="human protocol decision is missing"):
        run_native_official.run(
            "bfcl", CONFIG, output, tmp_path / "absent_snapshot_manifest.json",
            approval_path=tmp_path / "absent_approval.json",
        )
    assert not output.exists()


def test_blocked_bfcl_preflight_finalizes_verifiable_bundle(tmp_path, monkeypatch) -> None:
    preflight = BFCLPreflightResult(
        passed=False,
        reasons=("CUDA device unavailable",),
        details={"hardware": {
            "backend": "vllm", "backend_version": None,
            "torch_version": "2.15.0+cpu", "cuda_runtime_version": None,
        }},
    )

    def must_not_execute(plan, record_dir):
        raise AssertionError("blocked preflight must stop before native commands")

    snapshot, wheel = _install_bfcl_run_fixtures(
        monkeypatch, tmp_path, preflight=preflight, execute=must_not_execute,
    )
    output = tmp_path / "blocked-bundle"
    summary_path = run_native_official.run(
        "bfcl", CONFIG, output, snapshot, package_wheel=wheel,
        approval_path=tmp_path / "test-only-approval.json",
    )

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["overall"] == "BLOCKED"
    assert summary["execution_status"] == "BLOCKED_BEFORE_MODEL_ACCESS"
    assert summary["torch_version"] == "2.15.0+cpu"
    assert summary["validation_executions"] == summary["test_executions"] == 0
    assert verify_bundle(output, expected_kind="bfcl_official").run_id == "bfcl-fixture"


def test_successful_bfcl_runner_finalizes_strictly_verifiable_bundle(tmp_path, monkeypatch) -> None:
    hardware = {
        "backend": "vllm", "backend_version": PINNED_BACKEND_VERSION,
        "torch_version": f"{PINNED_TORCH_VERSION}+cu130",
        "cuda_runtime_version": PINNED_CUDA_VERSION,
    }
    preflight = BFCLPreflightResult(passed=True, reasons=(), details={"hardware": hardware})

    def execute_fixture_native_plan(plan, record_dir):
        """Write deterministic temporary fixtures; no BFCL package/model is run."""
        raw = Path(plan.output_dir)
        raw.mkdir(parents=True)
        for category in PHASE1_CATEGORIES:
            (raw / f"{category}.json").write_text(
                json.dumps([{"id": f"fixture-{category}", "success": True, "valid": True}]),
                encoding="utf-8",
            )
        record_dir.mkdir(parents=True)
        (record_dir / "plan.json").write_text(
            json.dumps({"commands": [list(command) for command in plan.commands]}),
            encoding="utf-8",
        )
        records = []
        for index, command in enumerate(plan.commands):
            record = {"index": index, "command": list(command), "exit_code": 0,
                      "stdout": "test-only fixture", "stderr": ""}
            (record_dir / f"command_{index}.json").write_text(json.dumps(record), encoding="utf-8")
            records.append(record)
        return tuple(records)

    snapshot, wheel = _install_bfcl_run_fixtures(
        monkeypatch, tmp_path, preflight=preflight, execute=execute_fixture_native_plan,
    )
    output = tmp_path / "successful-fixture-bundle"
    summary_path = run_native_official.run(
        "bfcl", CONFIG, output, snapshot, package_wheel=wheel,
        approval_path=tmp_path / "test-only-approval.json",
    )

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["overall"] == "PASS"
    assert summary["execution_status"] == "COMPLETE"
    assert summary["inference_backend_version"] == PINNED_BACKEND_VERSION
    assert summary["torch_version"] == f"{PINNED_TORCH_VERSION}+cu130"
    assert summary["cuda_runtime_version"] == PINNED_CUDA_VERSION
    assert summary["categories"] == list(PHASE1_CATEGORIES)
    assert summary["limitations"]
    assert verify_bundle(output, expected_kind="bfcl_official").run_id == "bfcl-fixture"
    assert verify_bfcl_bundle(output)["verified"] is True


def test_bfcl_external_runner_supports_documented_script_invocation() -> None:
    """The documented script path must import repository packages standalone."""
    script = Path("scripts/benchmark_bfcl_external_runner.py").resolve()
    result = subprocess.run(
        [sys.executable, str(script), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Run official BFCL benchmark" in result.stdout
