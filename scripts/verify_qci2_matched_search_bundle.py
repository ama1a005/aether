"""Independently verify a retained CORE-02 matched-search bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


METHODS = {"matched_random", "greedy", "beam", "receiver_only", "flat_ppo"}
SEEDS = {11, 22, 33}
TERMINAL = {"COMPLETE", "COMPLETE_NEGATIVE", "INCOMPLETE_BUDGET"}


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(root: Path) -> dict[str, Any]:
    """Reject altered, incomplete, over-budget or protected-split evidence."""
    root = root.resolve()
    required = {"manifest.json", "preflight.json", "candidate_graph.json",
                "raw_evaluations.jsonl", "budget_ledger.json", "edge_evidence.json",
                "search_results.json", "controls.json", "summary.json",
                "archive_contents.json"}
    missing = sorted(name for name in required if not (root / name).is_file())
    if missing:
        raise FileNotFoundError(f"CORE-02 bundle missing files: {missing}")
    summary = json.loads((root / "summary.json").read_text(encoding="utf-8"))
    preflight = json.loads((root / "preflight.json").read_text(encoding="utf-8"))
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    if preflight.get("overall") != "PASS" or preflight.get("model_accessed") is not False:
        raise ValueError("CORE-02 preflight is not a passing pre-access record")
    if manifest.get("uncommitted_diff") is not False:
        raise ValueError("CORE-02 evidence source was dirty")
    if any(summary.get(name) != 0 for name in
           ("development_audit_executions", "validation_executions", "test_executions")):
        raise PermissionError("CORE-02 accessed a protected split")
    if summary.get("status") not in TERMINAL:
        raise ValueError("CORE-02 summary is not in a retained terminal state")
    inventory = json.loads((root / "archive_contents.json").read_text(encoding="utf-8"))
    for relative, expected in inventory.items():
        path = (root / relative).resolve()
        if root not in path.parents or not path.is_file() or _hash(path) != expected:
            raise ValueError(f"CORE-02 archive hash failure: {relative}")
    ledgers = json.loads((root / "budget_ledger.json").read_text(encoding="utf-8"))
    identities = {(row["method"], int(row["seed"])) for row in ledgers}
    if identities != {(method, seed) for method in METHODS for seed in SEEDS}:
        raise ValueError("CORE-02 does not contain all 15 independent method/seed ledgers")
    namespaces = [row["cache_namespace"] for row in ledgers]
    if len(namespaces) != len(set(namespaces)):
        raise ValueError("CORE-02 cache namespaces are shared")
    for row in ledgers:
        if (row["unique_search_masks"] > 32 or row["mask_evaluations"] > 45
                or row["model_forward_steps"] > 7360):
            raise ValueError("CORE-02 matched budget exceeded")
    rows = [json.loads(line) for line in (root / "raw_evaluations.jsonl").read_text(encoding="utf-8").splitlines() if line]
    for row in rows:
        if row.get("evidence_type") != "real_model_intervention":
            raise ValueError("CORE-02 contains non-real evaluator evidence")
        if row.get("split") != "development_discovery":
            raise PermissionError("CORE-02 raw row uses a forbidden split")
        if row.get("forward_passes") != 160:
            raise ValueError("CORE-02 raw mask accounting differs from v2.2")
    edges = json.loads((root / "edge_evidence.json").read_text(encoding="utf-8"))
    if any(row.get("status") == "supported" and row.get("evidence_type") != "real_model_intervention"
           for row in edges):
        raise ValueError("CORE-02 promoted an edge without real intervention evidence")
    return {"overall": "PASS", "status": summary["status"],
            "run_count": len(ledgers), "raw_evaluation_count": len(rows),
            "development_audit_executions": 0, "validation_executions": 0,
            "test_executions": 0}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.root), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
