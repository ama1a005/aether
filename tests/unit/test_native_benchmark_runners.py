"""Native runner tests validate command/provenance behavior without benchmarks."""
from pathlib import Path

import pytest

from benchmarks.native_runners import agentdojo_plan, bfcl_plan, execute_native_plan


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


def test_native_execution_requires_exact_installed_version(tmp_path):
    plan = bfcl_plan(package_version="definitely-not-installed", model="model",
                     categories=["simple"], output_dir=tmp_path / "results")
    with pytest.raises(RuntimeError, match="not installed|version mismatch"):
        execute_native_plan(plan, tmp_path / "record")
    assert not (tmp_path / "record").exists()
