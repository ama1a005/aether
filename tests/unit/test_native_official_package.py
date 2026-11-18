"""Model-free tests for official benchmark execution packages."""

from pathlib import Path
import subprocess
import sys

import pytest

from benchmarks import run_native_official
from benchmarks.run_native_official import build_plan


CONFIG = Path("configs/benchmarks/phase1_external.yaml")


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
