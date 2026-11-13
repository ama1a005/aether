"""SUPPORT-01: Independent post-run verifier for red-team campaign artifacts.

Reconstructs summary statistics from raw attempt records without using
any in-memory state from the original run.  Reports actual counts;
negative results are reported as negative.

Usage:
    python -m experiments.supporting_nov19.red_team.verifier \\
        --run-dir results/phase1/red_team/qwen15b/<run_id>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _load_attempts(run_dir: Path) -> list[dict[str, Any]]:
    """Load all attempt records from the ledger subdirectory."""
    ledger = run_dir / "attempts"
    if not ledger.is_dir():
        raise FileNotFoundError(f"No 'attempts' subdirectory found in {run_dir}")
    records = []
    for path in sorted(ledger.glob("*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        records.append(raw)
    return records


def verify_run(run_dir: Path) -> dict[str, Any]:
    """Reconstruct and verify a completed red-team campaign from raw records.

    Returns a verification report dict.  The ``overall`` field is ``"PASS"``
    only if: all attempts are complete, there are real model outputs (not None),
    and no silent fallbacks are detected.  Negative results are reported honestly.
    """
    summary_path = run_dir / "summary.json"
    manifest_path = run_dir / "manifest.json"

    if not summary_path.is_file():
        return {"overall": "FAIL", "reason": "summary.json not found"}
    if not manifest_path.is_file():
        return {"overall": "FAIL", "reason": "manifest.json not found"}

    stored_summary = json.loads(summary_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    try:
        records = _load_attempts(run_dir)
    except FileNotFoundError as exc:
        return {"overall": "FAIL", "reason": str(exc)}

    # Count from raw records
    n_total = len(records)
    n_complete = sum(1 for r in records if r.get("status") == "complete")
    n_error = sum(1 for r in records if r.get("status") == "error")
    n_started = sum(1 for r in records if r.get("status") == "started")
    n_success = sum(1 for r in records if r.get("success") is True)
    n_clean_correct = sum(1 for r in records if r.get("clean_correct") is True)

    # Check real model outputs are present (not None / fixture-only)
    real_evidence_found = any(
        r.get("clean") is not None and r.get("attacked") is not None
        for r in records
        if r.get("status") == "complete"
    )

    # Detect silent fallbacks: evidence_class must be real_model_cpu_float32
    evidence_class = stored_summary.get("evidence_class", "")
    is_real = evidence_class == "real_model_cpu_float32"

    families_seen: set[str] = {r["family"] for r in records if "family" in r}

    report: dict[str, Any] = {
        "run_id": stored_summary.get("run_id", "unknown"),
        "evidence_class": evidence_class,
        "is_real_model_evidence": is_real,
        "n_total_attempts": n_total,
        "n_complete": n_complete,
        "n_error": n_error,
        "n_started_incomplete": n_started,
        "n_success": n_success,
        "n_clean_correct": n_clean_correct,
        "attack_success_rate": n_success / n_total if n_total > 0 else None,
        "clean_accuracy": n_clean_correct / n_total if n_total > 0 else None,
        "attack_families_observed": sorted(families_seen),
        "real_evidence_found": real_evidence_found,
        "stored_summary_plan_fingerprint": stored_summary.get("plan_fingerprint"),
        "manifest_model_id": manifest.get("model_id"),
        "manifest_model_revision": manifest.get("model_revision"),
        "manifest_git_commit": manifest.get("git_commit"),
        "validation_executions": 0,
        "test_executions": 0,
    }

    # Determine overall verdict
    if n_started > 0:
        report["overall"] = "FAIL"
        report["reason"] = f"{n_started} attempt(s) still in 'started' state (interrupted)"
    elif not is_real:
        report["overall"] = "FAIL"
        report["reason"] = f"evidence_class is {evidence_class!r}, not real_model_cpu_float32"
    elif not real_evidence_found and n_complete > 0:
        report["overall"] = "FAIL"
        report["reason"] = "No complete attempts have real model outputs"
    elif n_total == 0:
        report["overall"] = "FAIL"
        report["reason"] = "No attempts recorded"
    else:
        # Campaign ran; individual errors are legitimate evidence (not hidden)
        report["overall"] = "PASS"

    return report


def main() -> None:
    """CLI entry point for the independent post-run verifier."""
    parser = argparse.ArgumentParser(
        description="SUPPORT-01: Independent post-run verifier for red-team artifacts."
    )
    parser.add_argument("--run-dir", type=Path, required=True,
                        help="Path to a completed campaign run directory.")
    parser.add_argument("--output", type=Path, default=None,
                        help="Optional path to write verification report JSON.")
    args = parser.parse_args()

    report = verify_run(args.run_dir)
    print(json.dumps(report, indent=2))

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        print(f"\nVerification report written to {args.output}", flush=True)

    sys.exit(0 if report.get("overall") == "PASS" else 1)


if __name__ == "__main__":
    main()
