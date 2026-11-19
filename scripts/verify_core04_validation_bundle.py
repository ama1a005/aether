"""Independently verify a retained CORE-04 validation bundle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from causal.remediation_freeze import frozen_text_hash_matches


ARMS = {"no_defense", "frozen_receiver_l20_h5"}
SEEDS = {11, 22, 33}
CASES = {f"v2_case_{index:03d}" for index in range(24, 32)}


def verify(root: Path) -> dict[str, Any]:
    """Reject altered, incomplete, over-budget, non-real, or test evidence."""
    root = root.resolve()
    required = {"manifest.json", "preflight.json", "raw_evaluations.jsonl",
                "budget_ledger.json", "arm_results.json", "statistics.json",
                "summary.json", "archive_contents.json"}
    missing = sorted(name for name in required if not (root / name).is_file())
    if missing:
        raise FileNotFoundError(f"CORE-04 bundle missing files: {missing}")
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    preflight = json.loads((root / "preflight.json").read_text(encoding="utf-8"))
    summary = json.loads((root / "summary.json").read_text(encoding="utf-8"))
    if preflight.get("overall") != "PASS" or preflight.get("model_accessed") is not False:
        raise ValueError("CORE-04 preflight is not a passing pre-access record")
    if manifest.get("uncommitted_diff") is not False:
        raise ValueError("CORE-04 evidence source was dirty")
    if summary.get("overall") != "PASS" or summary.get("execution_state") != "COMPLETE":
        raise ValueError("CORE-04 execution is incomplete")
    if summary.get("development_executions") != 0 or summary.get("test_executions") != 0:
        raise PermissionError("CORE-04 accessed development or test")
    if summary.get("deployable_without_oracle") is not False:
        raise ValueError("CORE-04 improperly claims oracle-free deployment")
    inventory = json.loads((root / "archive_contents.json").read_text(encoding="utf-8"))
    for relative, expected in inventory.items():
        path = (root / relative).resolve()
        if (root not in path.parents or not path.is_file()
                or not frozen_text_hash_matches(path, expected)):
            raise ValueError(f"CORE-04 archive hash failure: {relative}")
    ledger = json.loads((root / "budget_ledger.json").read_text(encoding="utf-8"))
    if {(row["arm"], int(row["seed"])) for row in ledger} != {
        (arm, seed) for arm in ARMS for seed in SEEDS
    } or any(row.get("state") != "COMPLETE" for row in ledger):
        raise ValueError("CORE-04 lacks six complete arm/seed ledgers")
    forwards = sum(int(row["model_forward_steps"]) for row in ledger)
    if forwards != 504 or summary.get("model_forward_steps") != 504:
        raise ValueError("CORE-04 forward accounting differs from 504")
    results = json.loads((root / "arm_results.json").read_text(encoding="utf-8"))
    if set(results) != {f"{arm}:{seed}" for arm in ARMS for seed in SEEDS}:
        raise ValueError("CORE-04 lacks all six arm/seed results")
    rows = [json.loads(line) for line in (root / "raw_evaluations.jsonl").read_text(encoding="utf-8").splitlines() if line]
    if len(rows) != 96 or summary.get("raw_evaluation_count") != 96:
        raise ValueError("CORE-04 raw evaluation count differs")
    expected_keys = {(case, arm, seed, condition) for case in CASES for arm in ARMS
                     for seed in SEEDS for condition in ("clean", "attacked")}
    observed_keys = set()
    for row in rows:
        if row.get("evidence_type") != "real_model_intervention":
            raise ValueError("CORE-04 includes non-real evidence")
        if row.get("split") != "validation":
            raise PermissionError("CORE-04 row uses a forbidden split")
        if row.get("status") != "ok":
            raise ValueError("CORE-04 completed bundle contains invalid/error row")
        observed_keys.add((row.get("case_id"), row.get("arm"), int(row.get("seed")), row.get("condition")))
    if observed_keys != expected_keys:
        raise ValueError("CORE-04 validation row coverage differs")
    if summary.get("scientific_outcome") not in {"VALIDATION_ACCEPTED", "VALIDATION_REJECTED"}:
        raise ValueError("CORE-04 scientific outcome is invalid")
    statistics = json.loads((root / "statistics.json").read_text(encoding="utf-8"))
    expected_open = summary["scientific_outcome"] == "VALIDATION_ACCEPTED"
    if statistics.get("test_gate_open") is not expected_open:
        raise ValueError("CORE-04 test gate disagrees with scientific outcome")
    return {"overall": "PASS", "execution_state": "COMPLETE",
            "scientific_outcome": summary["scientific_outcome"],
            "arm_seed_run_count": 6, "raw_evaluation_count": 96,
            "model_forward_steps": 504, "development_executions": 0,
            "validation_executions": 96, "test_executions": 0,
            "test_gate_open": expected_open}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("root", type=Path)
    print(json.dumps(verify(parser.parse_args().root), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
