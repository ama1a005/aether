"""Native runner tests validate command/provenance behavior without benchmarks."""
from pathlib import Path

import pytest

from benchmarks.native_runners import (
    agentdojo_plan,
    bfcl_plan,
    bfcl_qwen25_plan,
    execute_native_plan,
)


def test_official_command_plans_are_explicit(tmp_path):
    dojo = agentdojo_plan(package_version="1.2.3", suite="workspace", model="model",
                          benchmark_version="v1.2.2", output_dir=tmp_path / "dojo",
                          user_tasks=["user_task_0"], injection_tasks=["injection_task_0"],
                          attack="tool_knowledge")
    assert dojo.commands[0][-2:] == ("--attack", "tool_knowledge")
    assert "user_task_0" in dojo.commands[0]
    bfcl = bfcl_plan(package_version="2025.10.27.1", model="model",
                     categories=["simple"], output_dir=tmp_path / "bfcl",
                     partial_evaluation=True)
    assert len(bfcl.commands) == 2
    assert bfcl.commands[1][-1] == "--partial-eval"
    assert bfcl.result_scope == "official_partial_subset_nonleaderboard"
    assert bfcl.commands[0][bfcl.commands[0].index("--test-category") + 1] == "simple"


def test_qwen25_adapter_plan_pins_snapshot_and_labels_scope(tmp_path):
    plan = bfcl_qwen25_plan(
        package_version="2026.3.23",
        model_revision="abc123",
        snapshot_manifest=tmp_path / "snapshot.json",
        categories=["simple", "multiple"],
        output_dir=tmp_path / "bfcl",
        num_gpus=2,
    )
    assert plan.commands[0][1:3] == ("-m", "benchmarks.bfcl_qwen25")
    assert "abc123" in plan.commands[0]
    assert "simple,multiple" in plan.commands[0]
    assert plan.result_scope == "official_evaluator_aether_qwen25_adapter_complete_categories"


def test_native_execution_requires_exact_installed_version(tmp_path):
    plan = bfcl_plan(package_version="definitely-not-installed", model="model",
                     categories=["simple"], output_dir=tmp_path / "results")
    with pytest.raises(RuntimeError, match="not installed|version mismatch"):
        execute_native_plan(plan, tmp_path / "record")
    assert not (tmp_path / "record").exists()
