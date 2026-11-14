"""Independently verify one retained CORE-02 seed shard."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.verify_qci2_matched_search_bundle import METHODS, TERMINAL

ROOT = Path(__file__).resolve().parents[1]
AMENDMENT = ROOT / "configs/phase1_core/qci2_method_freeze_v2_4_parallel_amendment.yaml"
DECISION = ROOT / "results/phase1/method_freeze/amendment_v2_4_parallel_decision.json"


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(root: Path) -> dict[str, Any]:
    """Reject incomplete, mixed-seed, altered or unauthorized shard evidence."""
    root = root.resolve()
    required = {"manifest.json", "preflight.json", "candidate_graph.json",
                "raw_evaluations.jsonl", "budget_ledger.json", "edge_evidence.json",
                "search_results.json", "controls.json", "summary.json",
                "archive_contents.json"}
    missing = sorted(name for name in required if not (root / name).is_file())
    if missing:
        raise FileNotFoundError(f"CORE-02 shard missing files: {missing}")
    if not DECISION.is_file():
        raise PermissionError("v2.4 parallel decision artifact is absent")
    decision = json.loads(DECISION.read_text(encoding="utf-8"))
    amendment_hash = _hash(AMENDMENT)
    if decision.get("decision") != "APPROVED" or decision.get("amendment_sha256") != amendment_hash:
        raise PermissionError("v2.4 parallel amendment is not exactly approved")
    summary = json.loads((root / "summary.json").read_text(encoding="utf-8"))
    preflight = json.loads((root / "preflight.json").read_text(encoding="utf-8"))
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    seeds = summary.get("seeds")
    if summary.get("execution_mode") != "seed_shard" or not isinstance(seeds, list) or len(seeds) != 1:
        raise ValueError("CORE-02 shard must declare exactly one seed")
    seed = int(seeds[0])
    if seed not in {11, 22, 33} or manifest.get("seeds") != [seed]:
        raise ValueError("CORE-02 shard seed provenance differs")
    if manifest.get("parallel_amendment_sha256") != amendment_hash:
        raise ValueError("CORE-02 shard uses a different parallel amendment")
    if preflight.get("overall") != "PASS" or preflight.get("model_accessed") is not False:
        raise ValueError("CORE-02 shard preflight is not a passing pre-access record")
    if manifest.get("uncommitted_diff") is not False or summary.get("status") not in TERMINAL:
        raise ValueError("CORE-02 shard source is dirty or nonterminal")
    if any(summary.get(name) != 0 for name in
           ("development_audit_executions", "validation_executions", "test_executions")):
        raise PermissionError("CORE-02 shard accessed a protected split")
    inventory = json.loads((root / "archive_contents.json").read_text(encoding="utf-8"))
    for relative, expected in inventory.items():
        path = (root / relative).resolve()
        if root not in path.parents or not path.is_file() or _hash(path) != expected:
            raise ValueError(f"CORE-02 shard archive hash failure: {relative}")
    ledgers = json.loads((root / "budget_ledger.json").read_text(encoding="utf-8"))
    if {(row["method"], int(row["seed"])) for row in ledgers} != {(m, seed) for m in METHODS}:
        raise ValueError("CORE-02 shard lacks its five method runs")
    namespaces = [row["cache_namespace"] for row in ledgers]
    if len(namespaces) != len(set(namespaces)):
        raise ValueError("CORE-02 shard shares method caches")
    for row in ledgers:
        if row["unique_search_masks"] > 32 or row["mask_evaluations"] > 45 or row["model_forward_steps"] > 7360:
            raise ValueError("CORE-02 shard exceeded a frozen budget")
    rows = [json.loads(line) for line in (root / "raw_evaluations.jsonl").read_text(encoding="utf-8").splitlines() if line]
    identities: set[tuple[str, int, tuple[str, ...]]] = set()
    for row in rows:
        identity = (row["method"], int(row["seed"]), tuple(row["mask"]))
        if identity in identities:
            raise ValueError("CORE-02 shard contains a duplicate mask evaluation")
        identities.add(identity)
        if (identity[0] not in METHODS or identity[1] != seed
                or row.get("evidence_type") != "real_model_intervention"
                or row.get("split") != "development_discovery"
                or row.get("forward_passes") != 160):
            raise ValueError("CORE-02 shard contains foreign or invalid raw evidence")
    return {"overall": "PASS", "seed": seed, "run_count": 5,
            "raw_evaluation_count": len(rows), "status": summary["status"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    print(json.dumps(verify(parser.parse_args().root), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
