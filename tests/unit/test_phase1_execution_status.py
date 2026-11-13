"""Tests for the dependency-aware Phase-1 execution registry."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from scripts.phase1_execution_status import DEFAULT_REGISTRY, execution_status


def test_repository_execution_registry_exactly_covers_evidence_gates() -> None:
    report = execution_status()
    rows = {row["id"]: row for row in report["stages"]}
    assert report["overall_evidence"] == "INCOMPLETE"
    assert rows["qwen_qualification"]["readiness"] == "COMPLETE"
    assert rows["matched_search_baselines"]["readiness"] == "READY_FOR_DECLARED_EXECUTION"
    assert rows["mechanism_guided_remediation"]["readiness"] == "BLOCKED_BY_DEPENDENCY"
    assert rows["mcptox_official"]["readiness"] == "BLOCKED_BY_PROTOCOL_OR_RESOURCE"
    assert rows["matched_search_baselines"]["runner_exists"] is True


def _write_registry(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "registry.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def test_registry_rejects_unknown_dependency_and_cycle(tmp_path: Path) -> None:
    base = yaml.safe_load(DEFAULT_REGISTRY.read_text(encoding="utf-8"))
    unknown = deepcopy(base)
    unknown["stages"]["qwen_qualification"]["depends_on"] = ["absent"]
    with pytest.raises(ValueError, match="unknown dependency"):
        execution_status(registry_path=_write_registry(tmp_path, unknown))
    cycle = deepcopy(base)
    cycle["stages"]["qwen_qualification"]["depends_on"] = ["qwen_instrumentation_acceptance"]
    with pytest.raises(ValueError, match="dependency cycle"):
        execution_status(registry_path=_write_registry(tmp_path, cycle))


def test_registry_rejects_unsafe_runner_path(tmp_path: Path) -> None:
    payload = yaml.safe_load(DEFAULT_REGISTRY.read_text(encoding="utf-8"))
    payload["stages"]["matched_search_baselines"]["runner"] = "../outside.ipynb"
    with pytest.raises(ValueError, match="unsafe"):
        execution_status(registry_path=_write_registry(tmp_path, payload))
