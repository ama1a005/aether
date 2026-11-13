"""Model-free tests for official benchmark execution packages."""

from pathlib import Path

import pytest

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
