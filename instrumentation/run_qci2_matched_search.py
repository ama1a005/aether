"""Run the approved, resumable CORE-02 real-Qwen matched-search campaign."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import tarfile
import time
from typing import Any

import torch

from causal.core_search import build_run_plans, load_effective_method_freeze, run_constraint_safe_search
from discovery.budgeted import Evaluation
from instrumentation.adapters import Qwen2ModelAdapter
from instrumentation.qci2_matched_evaluator import QwenMatchedMaskEvaluator


ROOT = Path(__file__).resolve().parents[1]
QUALIFICATION = ROOT / "results/phase1/model_qualification/qwen15b_kaggle_20261110/mq_g1_rows.json"
PROPOSAL = ROOT / "configs/phase1_core/qci2_method_freeze_v2.yaml"
V21 = ROOT / "configs/phase1_core/qci2_method_freeze_v2_1_amendment.yaml"
V22 = ROOT / "configs/phase1_core/qci2_method_freeze_v2_2_amendment.yaml"
V23 = ROOT / "configs/phase1_core/qci2_method_freeze_v2_3_amendment.yaml"
DECISION = ROOT / "results/phase1/method_freeze/decision.json"
V22_DECISION = ROOT / "results/phase1/method_freeze/amendment_v2_2_decision.json"
V23_DECISION = ROOT / "results/phase1/method_freeze/amendment_v2_3_decision.json"
V24 = ROOT / "configs/phase1_core/qci2_method_freeze_v2_4_parallel_amendment.yaml"
V24_DECISION = ROOT / "results/phase1/method_freeze/amendment_v2_4_parallel_decision.json"
METHODS = ("greedy", "matched_random", "beam", "receiver_only", "flat_ppo")
ALL_SEEDS = (11, 22, 33)


def _hash(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return digest


def _write(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False), encoding="utf-8")
    temporary.replace(path)


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()


def _checkpoint_archive(output: Path) -> None:
    """Replace a portable archive after every completed method/seed unit."""
    target = output.parent / "aether-core02-checkpoint.tar.gz"
    temporary = target.with_suffix(".tmp")
    with tarfile.open(temporary, "w:gz") as bundle:
        bundle.add(output, arcname=output.name)
    temporary.replace(target)


def _require_parallel_approval() -> str:
    """Return the approved v2.4 hash or fail before model access."""
    observed = _hash(V24)
    if not V24_DECISION.is_file():
        raise PermissionError(
            f"parallel execution awaits exact-hash approval: {observed}"
        )
    decision = json.loads(V24_DECISION.read_text(encoding="utf-8"))
    if (decision.get("decision") != "APPROVED"
            or decision.get("amendment_sha256") != observed):
        raise PermissionError("parallel execution decision does not approve v2.4")
    return observed


class RecordingEvaluator:
    """Persist every completed real mask evaluation and reuse it on resume."""

    def __init__(self, execute: QwenMatchedMaskEvaluator, raw: Path,
                 method: str, seed: int) -> None:
        self.execute, self.raw, self.method, self.seed = execute, raw, method, seed
        self.cache: dict[tuple[str, ...], Evaluation] = {}
        if raw.is_file():
            for line in raw.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                if row["method"] == method and int(row["seed"]) == seed:
                    mask = tuple(row["mask"])
                    self.cache[mask] = Evaluation(
                        row["faithfulness"], row["benign_damage"],
                        row["forward_passes"], row["raw_outputs"],
                    )

    def __call__(self, mask: tuple[str, ...]) -> Evaluation:
        if mask in self.cache:
            return self.cache[mask]
        value = self.execute(mask)
        record = {"schema_version": "aether.core02-mask-evaluation.v1",
                  "evidence_type": "real_model_intervention",
                  "split": "development_discovery", "method": self.method,
                  "seed": self.seed, "mask": list(mask),
                  "faithfulness": value.faithfulness,
                  "benign_damage": value.benign_damage,
                  "forward_passes": value.forward_passes,
                  "raw_outputs": value.raw_outputs}
        with self.raw.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, sort_keys=True, allow_nan=False) + "\n")
            stream.flush()
        self.cache[mask] = value
        _checkpoint_archive(self.raw.parent)
        return value


def run(output: Path, snapshot: Path, *, resume: bool,
        seeds: tuple[int, ...] = ALL_SEEDS) -> dict[str, Any]:
    """Execute or resume complete method groups for the requested frozen seeds."""
    if not seeds or any(seed not in ALL_SEEDS for seed in seeds) or len(set(seeds)) != len(seeds):
        raise ValueError("seeds must be a non-empty unique subset of 11, 22, 33")
    parallel_sha = _require_parallel_approval() if seeds != ALL_SEEDS else None
    if output.exists() and not resume:
        raise FileExistsError("CORE-02 output exists; use --resume without deleting it")
    output.mkdir(parents=True, exist_ok=True)
    freeze = load_effective_method_freeze(
        repo=ROOT, proposal_path=PROPOSAL, amendment_path=V22,
        v2_1_amendment_path=V21, method_amendment_path=V23,
        proposal_decision_path=DECISION, amendment_decision_path=V22_DECISION,
        method_amendment_decision_path=V23_DECISION,
    )
    preflight_path = output / "preflight.json"
    if not preflight_path.is_file() or json.loads(preflight_path.read_text())["overall"] != "PASS":
        raise RuntimeError("a passing pre-access preflight.json is required")
    if snapshot.name != freeze.proposal["model"]["revision"]:
        raise ValueError("model snapshot directory is not the pinned revision")
    rows = json.loads(QUALIFICATION.read_text(encoding="utf-8"))
    adapter = Qwen2ModelAdapter(str(snapshot), freeze.proposal["model"]["revision"],
                                snapshot.parent, dtype=torch.float32, device="cpu",
                                local_files_only=True, low_cpu_mem_usage=True)
    adapter.load()
    adapter.tokenizer.padding_side = "left"
    evaluator = QwenMatchedMaskEvaluator(adapter, freeze.proposal, rows)
    evaluator.capture_clean_sources()
    raw = output / "raw_evaluations.jsonl"
    checkpoint_path = output / "checkpoint_state.json"
    checkpoint = json.loads(checkpoint_path.read_text()) if checkpoint_path.is_file() else {"completed": {}}
    results: dict[str, Any] = dict(checkpoint.get("completed", {}))
    greedy_refs: dict[int, tuple[str, ...]] = {}
    plans = {(plan.method, plan.seed): plan for plan in build_run_plans(freeze)}
    started = time.perf_counter()
    for seed in seeds:
        for method in METHODS:
            key = f"{method}:{seed}"
            if key in results:
                if method == "greedy": greedy_refs[seed] = tuple(results[key]["retained"])
                continue
            recording = RecordingEvaluator(evaluator, raw, method, seed)
            outcome = run_constraint_safe_search(
                freeze, plans[(method, seed)], recording,
                matched_random_reference=greedy_refs.get(seed),
            )
            payload = asdict(outcome)
            results[key] = payload
            if method == "greedy": greedy_refs[seed] = outcome.retained
            _write(checkpoint_path, {"schema_version": "aether.core02-checkpoint.v1",
                                     "completed": results, "last_completed": key,
                                     "development_audit_executions": 0,
                                     "validation_executions": 0, "test_executions": 0})
            _checkpoint_archive(output)
    ledgers = [{"method": method, "seed": seed,
                "cache_namespace": plans[(method, seed)].cache_namespace,
                **results[f"{method}:{seed}"]["ledger"]}
               for seed in seeds for method in METHODS]
    _write(output / "budget_ledger.json", ledgers)
    _write(output / "search_results.json", results)
    _write(output / "candidate_graph.json", freeze.proposal["candidate_graph"])
    _write(output / "controls.json", {"status": "RESERVED_FOR_CORE03_EDGE_CONTROLS", "rows": []})
    _write(output / "edge_evidence.json", [
        {**edge, "status": "insufficient", "evidence_type": "none_search_does_not_promote_edges"}
        for edge in freeze.proposal["candidate_graph"]["edges"]
    ])
    status = "INCOMPLETE_BUDGET" if any(row["state"] == "INCOMPLETE_BUDGET" for row in ledgers) else "COMPLETE"
    summary = {"schema_version": "aether.core02-summary.v1", "status": status,
               "experiment_id": freeze.proposal["experiment_id"],
               "method_seed_run_count": len(results), "runtime_seconds": time.perf_counter() - started,
               "execution_mode": "complete" if seeds == ALL_SEEDS else "seed_shard",
               "seeds": list(seeds),
               "development_audit_executions": 0, "validation_executions": 0,
               "test_executions": 0,
               "claim_boundary": freeze.proposal["claim_boundary"]}
    _write(output / "summary.json", summary)
    manifest = {"schema_version": "aether.core02-manifest.v1",
                "utc_timestamp": datetime.now(timezone.utc).isoformat(),
                "git_commit": _git("rev-parse", "HEAD"),
                "uncommitted_diff": bool(_git("status", "--porcelain")),
                "model_id": freeze.proposal["model"]["id"],
                "model_revision": freeze.proposal["model"]["revision"],
                "python": platform.python_version(), "command_line": sys.argv,
                "proposal_sha256": freeze.proposal_sha256,
                "accounting_amendment_sha256": freeze.amendment_sha256,
                "method_amendment_sha256": freeze.method_amendment_sha256,
                "parallel_amendment_sha256": parallel_sha,
                "seeds": list(seeds)}
    _write(output / "manifest.json", manifest)
    inventory = {path.relative_to(output).as_posix(): _hash(path)
                 for path in sorted(output.rglob("*")) if path.is_file()
                 and path.name != "archive_contents.json"}
    _write(output / "archive_contents.json", inventory)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model-snapshot", type=Path, required=True)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--seed", type=int, choices=ALL_SEEDS)
    args = parser.parse_args()
    seeds = (args.seed,) if args.seed is not None else ALL_SEEDS
    print(json.dumps(run(args.output.resolve(), args.model_snapshot.resolve(),
                         resume=args.resume, seeds=seeds), indent=2))


if __name__ == "__main__":
    main()
