"""Independently verify a retained CORE-03 remediation bundle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from causal.remediation_freeze import sha256_file


ARMS = {"no_defense", "fixed_message_whole", "fixed_receiver_l22_attention",
        "mechanism_message_decision_code", "mechanism_receiver_l20_h5"}
SEEDS = {11, 22, 33}


def verify(root: Path) -> dict[str, Any]:
    """Reject altered, incomplete, over-budget, non-real, or protected-split evidence."""
    root = root.resolve()
    required = {"manifest.json", "preflight.json", "raw_evaluations.jsonl",
                "budget_ledger.json", "arm_results.json", "statistics.json",
                "summary.json", "archive_contents.json"}
    missing = sorted(name for name in required if not (root / name).is_file())
    if missing:
        raise FileNotFoundError(f"CORE-03 bundle missing files: {missing}")
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    preflight = json.loads((root / "preflight.json").read_text(encoding="utf-8"))
    summary = json.loads((root / "summary.json").read_text(encoding="utf-8"))
    if preflight.get("overall") != "PASS" or preflight.get("model_accessed") is not False:
        raise ValueError("CORE-03 preflight is not a passing pre-access record")
    if manifest.get("uncommitted_diff") is not False:
        raise ValueError("CORE-03 evidence source was dirty")
    if summary.get("overall") != "PASS" or summary.get("execution_state") != "COMPLETE":
        raise ValueError("CORE-03 execution is incomplete")
    if summary.get("validation_executions") != 0 or summary.get("test_executions") != 0:
        raise PermissionError("CORE-03 accessed validation or test")
    if summary.get("deployable_without_oracle") is not False:
        raise ValueError("CORE-03 improperly claims oracle-free deployment")
    inventory = json.loads((root / "archive_contents.json").read_text(encoding="utf-8"))
    for relative, expected in inventory.items():
        path = (root / relative).resolve()
        if root not in path.parents or not path.is_file() or sha256_file(path) != expected:
            raise ValueError(f"CORE-03 archive hash failure: {relative}")
    ledger = json.loads((root / "budget_ledger.json").read_text(encoding="utf-8"))
    if {(row["arm"], int(row["seed"])) for row in ledger} != {
        (arm, seed) for arm in ARMS for seed in SEEDS
    }:
        raise ValueError("CORE-03 lacks all 15 arm/seed ledgers")
    if any(row.get("state") != "COMPLETE" for row in ledger):
        raise ValueError("CORE-03 contains incomplete ledger rows")
    if sum(int(row["model_forward_steps"]) for row in ledger) > 624:
        raise ValueError("CORE-03 exceeded the frozen forward budget")
    results = json.loads((root / "arm_results.json").read_text(encoding="utf-8"))
    if set(results) != {f"{arm}:{seed}" for arm in ARMS for seed in SEEDS}:
        raise ValueError("CORE-03 lacks all 15 arm/seed results")
    rows = [json.loads(line) for line in (root / "raw_evaluations.jsonl").read_text(encoding="utf-8").splitlines() if line]
    if len(rows) != 120 or summary.get("raw_evaluation_count") != 120:
        raise ValueError("CORE-03 raw evaluation count differs")
    for row in rows:
        if row.get("evidence_type") != "real_model_intervention":
            raise ValueError("CORE-03 includes non-real evidence")
        if row.get("split") != "development_audit":
            raise PermissionError("CORE-03 row uses a forbidden split")
        if row.get("status") != "ok":
            raise ValueError("CORE-03 completed bundle contains invalid/error row")
    if summary.get("scientific_outcome") not in {
        "SELECTED_DEVELOPMENT_REPAIR", "COMPLETE_NO_FEASIBLE_REPAIR"
    }:
        raise ValueError("CORE-03 scientific outcome is invalid")
    return {"overall": "PASS", "execution_state": "COMPLETE",
            "scientific_outcome": summary["scientific_outcome"],
            "selected_arm": summary.get("selected_arm"), "arm_seed_run_count": 15,
            "raw_evaluation_count": 120, "model_forward_steps": sum(row["model_forward_steps"] for row in ledger),
            "validation_executions": 0, "test_executions": 0}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    print(json.dumps(verify(parser.parse_args().root), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
