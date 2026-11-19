"""Independently verify the retained once-only CORE-05 test bundle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from causal.remediation_freeze import sha256_file


ARMS = {"no_defense", "frozen_receiver_l20_h5"}; SEEDS = {11, 22, 33}
CASES = {f"v2_case_{index:03d}" for index in range(32, 40)}


def verify(root: Path) -> dict[str, Any]:
    """Reject altered, repeated, incomplete, over-budget, or wrong-split evidence."""
    root = root.resolve()
    required = {"manifest.json", "preflight.json", "attempt_marker.json", "raw_evaluations.jsonl",
                "budget_ledger.json", "arm_results.json", "statistics.json", "summary.json", "archive_contents.json"}
    missing = sorted(name for name in required if not (root / name).is_file())
    if missing:
        raise FileNotFoundError(f"CORE-05 bundle missing files: {missing}")
    load = lambda name: json.loads((root / name).read_text(encoding="utf-8"))
    manifest, preflight, marker, summary = load("manifest.json"), load("preflight.json"), load("attempt_marker.json"), load("summary.json")
    if preflight.get("overall") != "PASS" or preflight.get("model_accessed") is not False:
        raise ValueError("CORE-05 preflight is not a passing pre-access record")
    if manifest.get("uncommitted_diff") is not False:
        raise ValueError("CORE-05 source was dirty")
    attempt_id = marker.get("attempt_id")
    if not attempt_id or marker.get("state") != "COMPLETE" or manifest.get("attempt_id") != attempt_id or summary.get("attempt_id") != attempt_id:
        raise ValueError("CORE-05 attempt identity or completion state differs")
    if summary.get("overall") != "PASS" or summary.get("execution_state") != "COMPLETE":
        raise ValueError("CORE-05 execution is incomplete")
    if summary.get("development_executions") != 0 or summary.get("validation_executions") != 0:
        raise PermissionError("CORE-05 re-accessed development or validation")
    if summary.get("deployable_without_oracle") is not False:
        raise ValueError("CORE-05 improperly claims oracle-free deployment")
    for relative, expected in load("archive_contents.json").items():
        path = (root / relative).resolve()
        if root not in path.parents or not path.is_file() or sha256_file(path) != expected:
            raise ValueError(f"CORE-05 archive hash failure: {relative}")
    ledger = load("budget_ledger.json")
    if {(row["arm"], int(row["seed"])) for row in ledger} != {(arm, seed) for arm in ARMS for seed in SEEDS} or any(row.get("state") != "COMPLETE" for row in ledger):
        raise ValueError("CORE-05 lacks six complete ledgers")
    if sum(int(row["model_forward_steps"]) for row in ledger) != 504 or summary.get("model_forward_steps") != 504:
        raise ValueError("CORE-05 forward accounting differs from 504")
    if set(load("arm_results.json")) != {f"{arm}:{seed}" for arm in ARMS for seed in SEEDS}:
        raise ValueError("CORE-05 lacks all six results")
    rows = [json.loads(line) for line in (root / "raw_evaluations.jsonl").read_text().splitlines() if line]
    if len(rows) != 96 or summary.get("raw_evaluation_count") != 96 or summary.get("test_executions") != 96:
        raise ValueError("CORE-05 test row count differs")
    expected = {(case, arm, seed, condition) for case in CASES for arm in ARMS for seed in SEEDS for condition in ("clean", "attacked")}
    observed = set()
    for row in rows:
        if row.get("evidence_type") != "real_model_intervention" or row.get("status") != "ok":
            raise ValueError("CORE-05 contains non-real or failed evidence")
        if row.get("split") != "test":
            raise PermissionError("CORE-05 row uses a forbidden split")
        observed.add((row.get("case_id"), row.get("arm"), int(row.get("seed")), row.get("condition")))
    if observed != expected:
        raise ValueError("CORE-05 row coverage differs")
    if summary.get("scientific_outcome") not in {"TEST_ACCEPTED", "TEST_REJECTED"}:
        raise ValueError("CORE-05 outcome differs")
    return {"overall": "PASS", "execution_state": "COMPLETE", "scientific_outcome": summary["scientific_outcome"],
            "attempt_id": attempt_id, "arm_seed_run_count": 6, "raw_evaluation_count": 96,
            "model_forward_steps": 504, "development_executions": 0, "validation_executions": 0,
            "test_executions": 96}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("root", type=Path)
    print(json.dumps(verify(parser.parse_args().root), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
