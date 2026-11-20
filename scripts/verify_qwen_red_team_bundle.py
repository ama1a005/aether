"""Strict scientific verifier for a real-Qwen development red-team bundle."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

from experiments.external_bundle import verify_bundle


def _validate_summary(summary: dict[str, Any], attempt_count: int) -> None:
    """Reject structurally complete bundles without usable red-team measurements."""
    if summary.get("overall") != "PASS":
        raise ValueError("red-team wrapper did not complete successfully")
    if summary.get("evidence_class") != "real_qwen_development_red_team":
        raise ValueError("red-team evidence class differs")
    if summary.get("validation_executions") != 0 or summary.get("test_executions") != 0:
        raise ValueError("red-team bundle accessed a protected split")
    campaign = summary.get("campaign")
    if not isinstance(campaign, dict) or not isinstance(campaign.get("overall"), dict):
        raise ValueError("red-team campaign summary is missing")
    overall = campaign["overall"]
    eligible = overall.get("eligible_attempts")
    errors = overall.get("errors")
    conditional = overall.get("conditional_eligible")
    if eligible != attempt_count or attempt_count != 48:
        raise ValueError("red-team attempt count differs from the frozen development plan")
    if not isinstance(errors, int) or errors < 0 or errors >= eligible:
        raise ValueError("red-team bundle has no usable error denominator")
    if not isinstance(conditional, int) or conditional < 1:
        raise ValueError("red-team bundle has no clean-correct attack pairs")
    if campaign.get("target_calls") != 2 * eligible:
        raise ValueError("red-team target-call accounting differs")


def verify(root: Path) -> dict[str, Any]:
    """Verify bundle hashes plus red-team-specific scientific completeness."""
    identity = verify_bundle(root, expected_kind="qwen_red_team")
    attempts = sorted((root / "attempts").glob("*.json"))
    if not attempts:
        raise ValueError("red-team bundle contains no attempt records")
    rows = [json.loads(path.read_text(encoding="utf-8")) for path in attempts]
    if any(row.get("status") not in {"complete", "error"} for row in rows):
        raise ValueError("red-team bundle contains an unfinished attempt")
    summary = json.loads((root / "summary.json").read_text(encoding="utf-8"))
    _validate_summary(summary, len(rows))
    result = asdict(identity)
    result.update({
        "attempt_count": len(rows),
        "error_count": summary["campaign"]["overall"]["errors"],
        "conditional_eligible": summary["campaign"]["overall"]["conditional_eligible"],
        "scientifically_usable": True,
    })
    return result


def main() -> None:
    """Verify one red-team bundle and print its accepted identity."""
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    print(json.dumps(verify(parser.parse_args().root), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
