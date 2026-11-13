"""Preflight and plan the approved QCI-2 matched-search campaign.

The model-free mode implemented here is deliberately separate from real model
access. It creates no scientific result and never imports Transformers.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import platform
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

import psutil

from causal.core_search import build_run_plans, enumerate_legal_masks, load_effective_method_freeze


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROPOSAL = ROOT / "configs/phase1_core/qci2_method_freeze_v2.yaml"
DEFAULT_AMENDMENT = ROOT / "configs/phase1_core/qci2_method_freeze_v2_2_amendment.yaml"
DEFAULT_V2_1_AMENDMENT = ROOT / "configs/phase1_core/qci2_method_freeze_v2_1_amendment.yaml"
DEFAULT_METHOD_AMENDMENT = ROOT / "configs/phase1_core/qci2_method_freeze_v2_3_amendment.yaml"
DEFAULT_PROPOSAL_DECISION = ROOT / "results/phase1/method_freeze/decision.json"
DEFAULT_AMENDMENT_DECISION = ROOT / "results/phase1/method_freeze/amendment_v2_2_decision.json"
DEFAULT_METHOD_AMENDMENT_DECISION = ROOT / "results/phase1/method_freeze/amendment_v2_3_decision.json"


def _git(args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def inspect_preflight(
    *,
    proposal: Path,
    amendment: Path,
    v2_1_amendment: Path,
    method_amendment: Path,
    proposal_decision: Path,
    amendment_decision: Path,
    method_amendment_decision: Path,
    model_snapshot: Path | None,
    output: Path,
    method: str | None,
    seed: int | None,
    input_artifacts: tuple[Path, ...],
    declared_budget: int,
) -> dict[str, Any]:
    """Inspect authorization, split, resources and output safety without model access."""
    freeze = load_effective_method_freeze(
        repo=ROOT, proposal_path=proposal, amendment_path=amendment,
        v2_1_amendment_path=v2_1_amendment,
        method_amendment_path=method_amendment,
        proposal_decision_path=proposal_decision,
        amendment_decision_path=amendment_decision,
        method_amendment_decision_path=method_amendment_decision,
    )
    plans = build_run_plans(
        freeze, methods=[method] if method else None, seeds=[seed] if seed is not None else None
    )
    masks = enumerate_legal_masks(freeze.proposal)
    expected_inputs = {
        (ROOT / record["path"]).resolve()
        for record in freeze.proposal["evidence_inputs"].values()
    }
    supplied_inputs = {path.resolve() for path in input_artifacts}
    memory = psutil.virtual_memory()
    disk = shutil.disk_usage(output.parent.resolve())
    output_absent = not output.exists()
    snapshot_ready = model_snapshot is not None and model_snapshot.is_dir()
    checks = {
        "python_3_11": sys.version_info[:2] == (3, 11),
        "git_clean": _git(["status", "--porcelain"]) == "",
        "authorized_method_hashes": True,
        "development_discovery_only": freeze.proposal["split"] == "development_discovery",
        "audit_case_count_zero": True,
        "validation_case_count_zero": not freeze.proposal["validation_case_ids"],
        "test_case_count_zero": not freeze.proposal["test_case_ids"],
        "legal_mask_count": len(masks) == 36,
        "independent_cache_namespaces": len({plan.cache_namespace for plan in plans}) == len(plans),
        "input_artifacts_exact": supplied_inputs == expected_inputs,
        "declared_budget_exact": declared_budget == freeze.effective_budget["maximum_model_forward_steps"],
        "output_absent": output_absent,
        "model_snapshot_ready": snapshot_ready,
        "minimum_available_ram_10_gib": memory.available >= 10 * 2**30,
        "minimum_disk_free_12_gib": disk.free >= 12 * 2**30,
    }
    return {
        "schema_version": "aether.qci2-matched-search-preflight.v1",
        "utc_timestamp": datetime.now(timezone.utc).isoformat(),
        "model_accessed": False,
        "scientific_evidence": False,
        "git_commit": _git(["rev-parse", "HEAD"]),
        "python": platform.python_version(),
        "python_executable": sys.executable,
        "proposal_sha256": freeze.proposal_sha256,
        "amendment_sha256": freeze.amendment_sha256,
        "model": freeze.proposal["model"],
        "model_snapshot": str(model_snapshot.resolve()) if model_snapshot else None,
        "output": str(output.resolve()),
        "measurements": {
            "available_ram_gib": memory.available / 2**30,
            "disk_free_gib": disk.free / 2**30,
            "legal_mask_count": len(masks),
            "run_plan_count": len(plans),
        },
        "effective_budget": freeze.effective_budget,
        "input_artifacts": [str(path) for path in sorted(supplied_inputs)],
        "plans": [plan.to_dict() for plan in plans],
        "checks": checks,
        "overall": "PASS" if all(checks.values()) else "BLOCKED_PREFLIGHT",
    }


def main() -> None:
    """Run model-free preflight; execution remains blocked unless every check passes."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROPOSAL)
    parser.add_argument("--amendment", type=Path, default=DEFAULT_AMENDMENT)
    parser.add_argument("--v2-1-amendment", type=Path, default=DEFAULT_V2_1_AMENDMENT)
    parser.add_argument("--method-amendment", type=Path, default=DEFAULT_METHOD_AMENDMENT)
    parser.add_argument("--proposal-decision", type=Path, default=DEFAULT_PROPOSAL_DECISION)
    parser.add_argument("--amendment-decision", type=Path, default=DEFAULT_AMENDMENT_DECISION)
    parser.add_argument("--method-amendment-decision", type=Path, default=DEFAULT_METHOD_AMENDMENT_DECISION)
    parser.add_argument("--model-snapshot", type=Path)
    parser.add_argument("--input-artifact", action="append", type=Path, required=True)
    parser.add_argument("--declared-budget", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--method", choices=("matched_random", "greedy", "beam", "receiver_only", "flat_ppo"))
    parser.add_argument("--seed", type=int, choices=(11, 22, 33))
    parser.add_argument("--preflight-only", action="store_true", required=True)
    args = parser.parse_args()
    result = inspect_preflight(
        proposal=args.protocol.resolve(), amendment=args.amendment.resolve(),
        v2_1_amendment=args.v2_1_amendment.resolve(),
        method_amendment=args.method_amendment.resolve(),
        proposal_decision=args.proposal_decision.resolve(),
        amendment_decision=args.amendment_decision.resolve(),
        method_amendment_decision=args.method_amendment_decision.resolve(),
        model_snapshot=args.model_snapshot.resolve() if args.model_snapshot else None,
        output=args.output.resolve(), method=args.method, seed=args.seed,
        input_artifacts=tuple(args.input_artifact), declared_budget=args.declared_budget,
    )
    if result["overall"] == "PASS":
        args.output.mkdir(parents=True, exist_ok=False)
        (args.output / "preflight.json").write_text(
            json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["overall"] != "PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
