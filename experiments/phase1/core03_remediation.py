"""Preflight and execute the approved restart-safe CORE-03 campaign."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tarfile
import time
from typing import Any

import psutil
import torch

from causal.remediation_freeze import load_and_validate_remediation_freeze, sha256_file
from instrumentation.adapters import Qwen2ModelAdapter
from instrumentation.core03_evaluator import Core03Evaluator


ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = ROOT / "configs/phase1_core/core03_remediation_freeze_v1.yaml"
DECISION = ROOT / "results/phase1/remediation_freeze/decision.json"
ROWS = ROOT / "results/phase1/model_qualification/qwen15b_kaggle_20261110/mq_g1_rows.json"
ARMS = ("no_defense", "fixed_message_whole", "fixed_receiver_l22_attention",
        "mechanism_message_decision_code", "mechanism_receiver_l20_h5")
SEEDS = (11, 22, 33)
COMPLEXITY = {
    "fixed_message_whole": (1, 0),
    "fixed_receiver_l22_attention": (0, 1),
    "mechanism_message_decision_code": (1, 0),
    "mechanism_receiver_l20_h5": (0, 1),
}


def _write(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False), encoding="utf-8")
    temporary.replace(path)


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()


def _authorization() -> tuple[dict[str, Any], str]:
    protocol = load_and_validate_remediation_freeze(PROTOCOL, ROOT)
    digest = sha256_file(PROTOCOL)
    decision = json.loads(DECISION.read_text(encoding="utf-8"))
    if decision.get("decision") != "APPROVED" or decision.get("proposal_sha256") != digest:
        raise PermissionError("CORE-03 lacks exact-hash human approval")
    return protocol, digest


def preflight(output: Path, snapshot: Path) -> dict[str, Any]:
    """Check authorization, immutable evidence, resources and split locks before model access."""
    protocol, digest = _authorization()
    memory = psutil.virtual_memory()
    checks = {
        "python_3_11": sys.version_info[:2] == (3, 11),
        "git_clean": _git("status", "--porcelain") == "",
        "exact_human_approval": True,
        "snapshot_revision": snapshot.is_dir() and snapshot.name == protocol["model"]["revision"],
        "output_absent": not output.exists(),
        "development_audit_exact": protocol["cohort"]["case_ids"] == [
            "v2_case_010", "v2_case_011", "v2_case_012", "v2_case_013"
        ],
        "validation_locked": not protocol["cohort"]["validation_case_ids"],
        "test_locked": not protocol["cohort"]["test_case_ids"],
        "ram_available_10_gib": memory.available >= 10 * 2**30,
    }
    return {
        "schema_version": "aether.core03-preflight.v1",
        "utc_timestamp": datetime.now(timezone.utc).isoformat(),
        "overall": "PASS" if all(checks.values()) else "BLOCKED_PREFLIGHT",
        "model_accessed": False, "scientific_evidence": False,
        "git_commit": _git("rev-parse", "HEAD"), "python": platform.python_version(),
        "proposal_sha256": digest, "model_snapshot": str(snapshot),
        "available_ram_gib": memory.available / 2**30, "checks": checks,
    }


def _archive(output: Path) -> Path:
    target = output.parent / "aether-core03-checkpoint.tar.gz"
    temporary = target.with_suffix(".tmp")
    with tarfile.open(temporary, "w:gz") as bundle:
        bundle.add(output, arcname=output.name)
    temporary.replace(target)
    return target


def _rebuild_raw(output: Path) -> None:
    """Atomically rebuild the combined JSONL from immutable completed unit files."""
    target = output / "raw_evaluations.jsonl"
    temporary = target.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        for seed in SEEDS:
            for arm in ARMS:
                unit = output / "units" / f"{arm}-{seed}.json"
                if not unit.is_file():
                    continue
                for row in json.loads(unit.read_text(encoding="utf-8"))["rows"]:
                    stream.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(target)


class CheckpointPublisher:
    """Upload each complete arm/seed checkpoint to an existing private dataset."""

    def __init__(self, repo_id: str, path_in_repo: str, token_env: str = "HF_TOKEN") -> None:
        from huggingface_hub import HfApi

        token = os.environ.get(token_env)
        if not token:
            raise RuntimeError(f"missing checkpoint token environment variable: {token_env}")
        self.api = HfApi(token=token)
        self.repo_id, self.path_in_repo = repo_id, path_in_repo
        info = self.api.repo_info(repo_id=repo_id, repo_type="dataset")
        if not bool(getattr(info, "private", False)):
            raise PermissionError("CORE-03 checkpoint dataset must already exist and be private")

    def publish(self, archive: Path, message: str) -> None:
        """Synchronously commit one complete archive before execution continues."""
        self.api.upload_file(path_or_fileobj=archive, path_in_repo=self.path_in_repo,
                             repo_id=self.repo_id, repo_type="dataset", commit_message=message)


def select_arm(completed: dict[str, dict[str, Any]]) -> tuple[str | None, dict[str, Any]]:
    """Apply the frozen arm-level feasibility and deterministic ordering rule."""
    aggregate: dict[str, Any] = {}
    for arm in ARMS[1:]:
        rows = [completed[f"{arm}:{seed}"] for seed in SEEDS]
        message_units, internal_components = COMPLEXITY[arm]
        aggregate[arm] = {
            "attacked_decision_recovery_accuracy": sum(
                row["attacked_decision_recovery_accuracy"] for row in rows
            ) / len(rows),
            "clean_decision_accuracy": sum(row["clean_decision_accuracy"] for row in rows) / len(rows),
            "invalid_or_error_fraction": sum(row["invalid_or_error_count"] for row in rows) / 12,
            "modified_message_units": message_units,
            "modified_internal_components": internal_components,
            "model_forward_steps": sum(row["model_forward_steps"] for row in rows),
        }
    feasible = [(arm, row) for arm, row in aggregate.items()
                if row["attacked_decision_recovery_accuracy"] >= 0.75
                and row["clean_decision_accuracy"] >= 1.0
                and row["invalid_or_error_fraction"] == 0.0]
    ordered = sorted(feasible, key=lambda item: (
        -item[1]["attacked_decision_recovery_accuracy"],
        -item[1]["clean_decision_accuracy"], item[1]["invalid_or_error_fraction"],
        item[1]["modified_message_units"], item[1]["modified_internal_components"],
        item[1]["model_forward_steps"], item[0],
    ))
    return (ordered[0][0] if ordered else None), aggregate


def run(output: Path, snapshot: Path, *, resume: bool,
        publisher: CheckpointPublisher | None = None) -> dict[str, Any]:
    """Run or resume all frozen arm/seed units, checkpointing every unit."""
    protocol, digest = _authorization()
    if output.exists() and not resume:
        raise FileExistsError("CORE-03 output exists; use --resume")
    preflight_path = output / "preflight.json"
    if not preflight_path.is_file() or json.loads(preflight_path.read_text())["overall"] != "PASS":
        raise RuntimeError("passing CORE-03 preflight required")
    adapter = Qwen2ModelAdapter(str(snapshot), protocol["model"]["revision"], snapshot.parent,
                                dtype=torch.float32, device="cpu", local_files_only=True,
                                low_cpu_mem_usage=True)
    adapter.load()
    adapter.tokenizer.padding_side = "left"
    evaluator = Core03Evaluator(adapter, protocol, json.loads(ROWS.read_text(encoding="utf-8")))
    checkpoint_path = output / "checkpoint_state.json"
    state = json.loads(checkpoint_path.read_text()) if checkpoint_path.is_file() else {"completed": {}}
    completed: dict[str, Any] = state["completed"]
    unit_dir = output / "units"
    unit_dir.mkdir(exist_ok=True)
    for seed in SEEDS:
        for arm in ARMS:
            key = f"{arm}:{seed}"
            unit_path = unit_dir / f"{arm}-{seed}.json"
            if unit_path.is_file() and key not in completed:
                recovered = json.loads(unit_path.read_text(encoding="utf-8"))
                completed[key] = {name: value for name, value in recovered.items() if name != "rows"}
    _rebuild_raw(output)
    started = time.perf_counter()
    for seed in SEEDS:
        for arm in ARMS:
            key = f"{arm}:{seed}"
            if key in completed:
                continue
            result = evaluator.evaluate_arm(arm, seed)
            unit_path = unit_dir / f"{arm}-{seed}.json"
            _write(unit_path, result)
            completed[key] = {name: value for name, value in result.items() if name != "rows"}
            _rebuild_raw(output)
            _write(checkpoint_path, {"schema_version": "aether.core03-checkpoint.v1",
                                     "completed": completed, "last_completed": key,
                                     "validation_executions": 0, "test_executions": 0})
            archive = _archive(output)
            if publisher is not None:
                publisher.publish(archive, f"CORE-03 completed {key}")
            print(f"completed CORE-03 unit {key} ({len(completed)}/15)", flush=True)
    _write(output / "arm_results.json", completed)
    ledgers = [{"arm": arm, "seed": seed, "state": "COMPLETE",
                "model_forward_steps": completed[f"{arm}:{seed}"]["model_forward_steps"]}
               for seed in SEEDS for arm in ARMS]
    _write(output / "budget_ledger.json", ledgers)
    selected, aggregate = select_arm(completed)
    outcome = "SELECTED_DEVELOPMENT_REPAIR" if selected else "COMPLETE_NO_FEASIBLE_REPAIR"
    statistics = {"schema_version": "aether.core03-statistics.v1",
                  "descriptive_only": True, "selected_arm": selected,
                  "aggregate_by_arm": aggregate,
                  "seed_stability": {arm: [completed[f"{arm}:{seed}"]["attacked_decision_recovery_accuracy"] for seed in SEEDS] for arm in ARMS}}
    _write(output / "statistics.json", statistics)
    summary = {"schema_version": "aether.core03-summary.v1", "overall": "PASS",
               "execution_state": "COMPLETE", "scientific_outcome": outcome,
               "selected_arm": statistics["selected_arm"], "arm_seed_run_count": 15,
               "raw_evaluation_count": 120, "model_forward_steps": sum(row["model_forward_steps"] for row in ledgers),
               "runtime_seconds": time.perf_counter() - started,
               "development_audit_executions": 120, "validation_executions": 0,
               "test_executions": 0, "deployable_without_oracle": False,
               "claim_boundary": protocol["claim_boundary"]}
    _write(output / "summary.json", summary)
    _write(output / "manifest.json", {
        "schema_version": "aether.core03-manifest.v1", "run_id": protocol["experiment_id"],
        "utc_timestamp": datetime.now(timezone.utc).isoformat(), "git_commit": _git("rev-parse", "HEAD"),
        "uncommitted_diff": bool(_git("status", "--porcelain")),
        "dataset_manifest_hashes": {key: value["sha256"] for key, value in protocol["evidence_inputs"].items()},
        "model_id": protocol["model"]["id"], "model_revision": protocol["model"]["revision"],
        "tokenizer_revision": protocol["model"]["revision"], "prompt_versions": {"source": "qualified_mq_g1_rows"},
        "random_seeds": list(SEEDS), "hardware": platform.platform(), "python_env_hash": None,
        "command_line": sys.argv, "config_file": str(PROTOCOL.relative_to(ROOT)),
        "raw_output_path": "raw_evaluations.jsonl", "proposal_sha256": digest,
    })
    inventory = {path.relative_to(output).as_posix(): sha256_file(path)
                 for path in sorted(output.rglob("*")) if path.is_file() and path.name != "archive_contents.json"}
    _write(output / "archive_contents.json", inventory)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--model-snapshot", required=True, type=Path)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--checkpoint-repo")
    parser.add_argument("--checkpoint-path", default="core03/checkpoint.tar.gz")
    args = parser.parse_args()
    output, snapshot = args.output.resolve(), args.model_snapshot.resolve()
    if args.preflight_only:
        result = preflight(output, snapshot)
        if result["overall"] == "PASS":
            output.mkdir(parents=True, exist_ok=False)
            _write(output / "preflight.json", result)
        print(json.dumps(result, indent=2))
        raise SystemExit(0 if result["overall"] == "PASS" else 2)
    publisher = CheckpointPublisher(args.checkpoint_repo, args.checkpoint_path) if args.checkpoint_repo else None
    print(json.dumps(run(output, snapshot, resume=args.resume, publisher=publisher), indent=2))


if __name__ == "__main__":
    main()
