"""Merge three independently verified CORE-02 seed shards."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any

from scripts.verify_qci2_matched_search_bundle import verify as verify_bundle
from scripts.verify_qci2_matched_search_shard import verify as verify_shard


def _write(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False), encoding="utf-8")


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def merge(shards: list[Path], output: Path) -> dict[str, Any]:
    """Verify and combine exactly seeds 11, 22 and 33 without recomputation."""
    if output.exists():
        raise FileExistsError(f"merge output already exists: {output}")
    verified = [(verify_shard(path), path.resolve()) for path in shards]
    if {item[0]["seed"] for item in verified} != {11, 22, 33} or len(verified) != 3:
        raise ValueError("exactly one verified shard for each seed is required")
    output.mkdir(parents=True)
    first = verified[0][1]
    for name in ("preflight.json", "candidate_graph.json", "controls.json", "edge_evidence.json"):
        shutil.copy2(first / name, output / name)
    ledgers: list[dict[str, Any]] = []
    results: dict[str, Any] = {}
    rows: list[dict[str, Any]] = []
    manifests: list[dict[str, Any]] = []
    identities: set[tuple[str, int, tuple[str, ...]]] = set()
    statuses: list[str] = []
    for check, shard in sorted(verified, key=lambda item: item[0]["seed"]):
        ledgers.extend(json.loads((shard / "budget_ledger.json").read_text(encoding="utf-8")))
        shard_results = json.loads((shard / "search_results.json").read_text(encoding="utf-8"))
        overlap = set(results).intersection(shard_results)
        if overlap:
            raise ValueError(f"duplicate method/seed results: {sorted(overlap)}")
        results.update(shard_results)
        for line in (shard / "raw_evaluations.jsonl").read_text(encoding="utf-8").splitlines():
            if not line:
                continue
            row = json.loads(line)
            identity = (row["method"], int(row["seed"]), tuple(row["mask"]))
            if identity in identities:
                raise ValueError(f"duplicate raw evaluation across shards: {identity}")
            identities.add(identity)
            rows.append(row)
        manifests.append(json.loads((shard / "manifest.json").read_text(encoding="utf-8")))
        statuses.append(check["status"])
    provenance = {(m["model_id"], m["model_revision"], m["proposal_sha256"],
                   m["accounting_amendment_sha256"], m["method_amendment_sha256"],
                   m["parallel_amendment_sha256"]) for m in manifests}
    if len(provenance) != 1:
        raise ValueError("shard scientific provenance differs")
    _write(output / "budget_ledger.json", ledgers)
    _write(output / "search_results.json", results)
    with (output / "raw_evaluations.jsonl").open("w", encoding="utf-8") as stream:
        for row in sorted(rows, key=lambda r: (int(r["seed"]), r["method"], tuple(r["mask"]))):
            stream.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
    status = "INCOMPLETE_BUDGET" if "INCOMPLETE_BUDGET" in statuses else "COMPLETE"
    _write(output / "summary.json", {"schema_version": "aether.core02-summary.v1",
        "status": status, "experiment_id": json.loads((first / "summary.json").read_text())["experiment_id"],
        "method_seed_run_count": 15, "execution_mode": "verified_seed_shard_merge",
        "development_audit_executions": 0, "validation_executions": 0,
        "test_executions": 0,
        "claim_boundary": json.loads((first / "summary.json").read_text())["claim_boundary"]})
    base = manifests[0]
    _write(output / "manifest.json", {**base,
        "schema_version": "aether.core02-merged-manifest.v1",
        "utc_timestamp": datetime.now(timezone.utc).isoformat(),
        "seeds": [11, 22, 33], "source_shard_manifest_sha256":
        {_hash(path / "manifest.json"): json.loads((path / "manifest.json").read_text())["seeds"]
         for _, path in verified}})
    inventory = {path.relative_to(output).as_posix(): _hash(path)
                 for path in sorted(output.rglob("*")) if path.is_file()
                 and path.name != "archive_contents.json"}
    _write(output / "archive_contents.json", inventory)
    return verify_bundle(output)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shard", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(merge(args.shard, args.output), indent=2))


if __name__ == "__main__":
    main()
