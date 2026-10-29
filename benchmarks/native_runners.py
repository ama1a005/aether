"""Fail-closed command plans for official BFCL and AgentDojo evaluators."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from importlib.metadata import PackageNotFoundError, version
import json
from pathlib import Path
import subprocess
import sys
from typing import Sequence


@dataclass(frozen=True)
class NativeBenchmarkPlan:
    """Pinned official-package invocation with an isolated artifact directory."""
    benchmark: str
    package: str
    package_version: str
    commands: tuple[tuple[str, ...], ...]
    output_dir: str
    result_scope: str


def agentdojo_plan(*, package_version: str, suite: str, model: str,
                   benchmark_version: str, output_dir: Path,
                   user_tasks: Sequence[str], injection_tasks: Sequence[str] = (),
                   attack: str | None = None, defense: str | None = None) -> NativeBenchmarkPlan:
    """Build an official AgentDojo CLI invocation for explicit task IDs."""
    if not all((package_version, suite, model, benchmark_version)) or not user_tasks:
        raise ValueError("Pinned AgentDojo metadata and user tasks are required")
    command = [sys.executable, "-m", "agentdojo.scripts.benchmark", "--suite", suite,
               "--model", model, "--benchmark-version", benchmark_version,
               "--logdir", str(output_dir.resolve()), "--max-workers", "1"]
    for task in user_tasks:
        command.extend(("--user-task", task))
    for task in injection_tasks:
        command.extend(("--injection-task", task))
    if attack:
        command.extend(("--attack", attack))
    if defense:
        command.extend(("--defense", defense))
    return NativeBenchmarkPlan("AgentDojo", "agentdojo", package_version,
                               (tuple(command),), str(output_dir.resolve()),
                               "official_selected_task_subset")


def bfcl_plan(*, package_version: str, model: str, categories: Sequence[str],
              output_dir: Path, partial_evaluation: bool = False) -> NativeBenchmarkPlan:
    """Build official BFCL generation and evaluation invocations."""
    if not package_version or not model or not categories or any(not item for item in categories):
        raise ValueError("Pinned BFCL metadata, model and categories are required")
    root = str(output_dir.resolve())
    common = ["--model", model, "--test-category", *categories, "--result-dir", root]
    generate = (sys.executable, "-m", "bfcl_eval", "generate", *common)
    evaluate = [sys.executable, "-m", "bfcl_eval", "evaluate", *common,
                "--score-dir", root]
    if partial_evaluation:
        evaluate.append("--partial-eval")
    scope = "official_partial_subset_nonleaderboard" if partial_evaluation else "official_complete_categories"
    return NativeBenchmarkPlan("BFCL", "bfcl_eval", package_version,
                               (tuple(generate), tuple(evaluate)), root, scope)


def execute_native_plan(plan: NativeBenchmarkPlan, record_dir: Path) -> tuple[dict[str, object], ...]:
    """Execute official commands only when the installed version exactly matches.

    Stdout, stderr and exit status are written after every command. A failure is
    retained and raised; later commands are not executed. Credentials are read by
    the official package environment and are never serialized here.
    """
    try:
        installed = version(plan.package)
    except PackageNotFoundError as exc:
        raise RuntimeError(f"Required official package is not installed: {plan.package}") from exc
    if installed != plan.package_version:
        raise RuntimeError(f"{plan.package} version mismatch: expected {plan.package_version}, got {installed}")
    record_dir.mkdir(parents=True, exist_ok=False)
    (record_dir / "plan.json").write_text(json.dumps(asdict(plan), indent=2), encoding="utf-8")
    records = []
    for index, command in enumerate(plan.commands):
        completed = subprocess.run(command, check=False, capture_output=True, text=True)
        record = {"index": index, "command": list(command), "exit_code": completed.returncode,
                  "stdout": completed.stdout, "stderr": completed.stderr}
        (record_dir / f"command_{index}.json").write_text(
            json.dumps(record, indent=2, allow_nan=False), encoding="utf-8")
        records.append(record)
        if completed.returncode:
            raise RuntimeError(f"{plan.benchmark} official command {index} failed; raw log retained")
    return tuple(records)
