"""Execute pinned BFCL or AgentDojo plans and retain an admissible raw bundle."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import platform
from pathlib import Path
import subprocess
import sys
from typing import Any

import yaml

from benchmarks.native_runners import NativeBenchmarkPlan, agentdojo_plan, bfcl_qwen25_plan, execute_native_plan
from experiments.external_bundle import sha256_file, write_bundle_manifest


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs/benchmarks/phase1_external.yaml"


def build_plan(benchmark: str, config_path: Path, output: Path, snapshot_manifest: Path | None) -> NativeBenchmarkPlan:
    """Build one pinned official-package plan without executing it."""
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if config.get("schema_version") != 1 or config.get("split") != "development":
        raise ValueError("official benchmark config must be schema 1 development preparation")
    if benchmark == "bfcl":
        if snapshot_manifest is None or not snapshot_manifest.is_file():
            raise FileNotFoundError("BFCL requires the qualified model snapshot manifest")
        item = config["bfcl"]
        return bfcl_qwen25_plan(
            package_version=str(item["package_version"]), model_revision=str(item["model_revision"]),
            snapshot_manifest=snapshot_manifest, categories=item["categories"], output_dir=output / "official_raw",
        )
    if benchmark == "agentdojo":
        item = config["agentdojo"]
        return agentdojo_plan(
            package_version=str(item["package_version"]), suite=str(item["suite"]), model=str(item["model"]),
            benchmark_version=str(item["benchmark_version"]), output_dir=output / "official_raw",
            user_tasks=item["user_tasks"], injection_tasks=item["injection_tasks"],
        )
    raise ValueError(f"unsupported official benchmark: {benchmark}")


def _command(command: list[str]) -> str:
    return subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()


def run(benchmark: str, config_path: Path, output: Path, snapshot_manifest: Path | None) -> Path:
    """Execute a native plan once and write a provenance-complete external bundle."""
    if output.exists():
        raise FileExistsError(f"output already exists: {output}")
    if _command(["git", "status", "--porcelain"]):
        raise RuntimeError("official evidence execution requires a clean source tree")
    plan = build_plan(benchmark, config_path, output, snapshot_manifest)
    output.mkdir(parents=True)
    records = execute_native_plan(plan, output / "command_records")
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))[benchmark]
    summary = {
        "schema_version": "aether.official-benchmark-summary.v1", "overall": "PASS",
        "benchmark": benchmark, "official_evaluator": True,
        "custom_model_adapter_disclosed": benchmark == "bfcl",
        "model_id": config["model"], "model_revision": config.get("model_revision", "official_runtime_managed"),
        "result_scope": plan.result_scope, "command_count": len(records),
        "all_commands_passed": all(record["exit_code"] == 0 for record in records),
        "metric_location": str(Path(plan.output_dir)),
        "validation_executions": 0, "test_executions": 0,
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    freeze = _command([sys.executable, "-m", "pip", "freeze", "--all"])
    metadata: dict[str, Any] = {
        "experiment_id": f"P0_{benchmark}_{datetime.now(timezone.utc):%Y%m%d}_official_0",
        "run_id": f"{benchmark}-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}",
        "utc_timestamp": datetime.now(timezone.utc).isoformat(), "git_commit": _command(["git", "rev-parse", "HEAD"]),
        "uncommitted_diff": False, "dataset_manifest_hashes": {"config": sha256_file(config_path)},
        "model_id": config["model"], "model_revision": str(config.get("model_revision", "official_runtime_managed")),
        "tokenizer_revision": str(config.get("model_revision", "official_runtime_managed")),
        "random_seeds": [0], "hardware": platform.platform(),
        "python_env_hash": hashlib.sha256(freeze.encode()).hexdigest(), "command_line": sys.argv,
        "config_file": str(config_path), "evidence_kind": f"{benchmark}_official",
        "validation_executions": 0, "test_executions": 0,
    }
    return write_bundle_manifest(output, metadata)


def main() -> None:
    """Run a selected pinned native benchmark."""
    parser = argparse.ArgumentParser()
    parser.add_argument("benchmark", choices=("bfcl", "agentdojo"))
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--snapshot-manifest", type=Path)
    arguments = parser.parse_args()
    print(run(arguments.benchmark, arguments.config, arguments.output, arguments.snapshot_manifest))


if __name__ == "__main__":
    main()
