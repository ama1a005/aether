"""Independently verify a downloaded QCI-A1 development-audit bundle."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
from typing import Any

from scripts.verify_qci_bundle import EXPECTED_OPERATORS, _resolve, _sha256


def verify_audit(root: Path) -> dict[str, Any]:
    """Verify QCI-A1 hashes, audit denominators, budgets and locked splits."""
    root = root.resolve()
    required = {
        "summary.json", "manifest.json", "raw_audit_interventions.jsonl",
        "candidate_audit_assessments.json", "message_positive_controls.json",
        "audit_preflight.json", "audit_model_access.json", "archive_contents.json",
    }
    missing = sorted(name for name in required if not (root / name).is_file())
    if missing:
        raise FileNotFoundError(f"QCI audit bundle is missing files: {missing}")
    summary = json.loads((root / "summary.json").read_text(encoding="utf-8"))
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    preflight = json.loads((root / "audit_preflight.json").read_text(encoding="utf-8"))
    marker = json.loads((root / "audit_model_access.json").read_text(encoding="utf-8"))
    if preflight["decision"]["overall"] != "PASS":
        raise ValueError("QCI audit preflight did not pass")
    if marker.get("state") != "QCI_AUDIT_COMPLETE":
        raise ValueError("QCI audit marker is not complete")
    if summary.get("validation_executions") != 0 or summary.get("test_executions") != 0:
        raise ValueError("QCI audit accessed a locked split")
    failures = []
    for recorded, expected in manifest["artifact_paths"].items():
        if _sha256(_resolve(root, recorded)) != expected:
            failures.append(recorded)
    if failures:
        raise ValueError(f"QCI audit manifest hash failures: {failures}")
    archive_contents = json.loads((root / "archive_contents.json").read_text(encoding="utf-8"))
    failures = []
    for recorded, expected in archive_contents.items():
        if _sha256(_resolve(root, recorded)) != expected:
            failures.append(recorded)
    if failures:
        raise ValueError(f"QCI audit archive-content hash failures: {failures}")
    rows = [
        json.loads(line) for line in
        (root / "raw_audit_interventions.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    by_candidate: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_candidate[str(row["candidate_id"])].append(row)
        if row.get("hook_cleanup") is not True:
            raise ValueError("QCI audit row did not clean up hooks")
        if row["operator"] != "passive_hook" and row.get("status") == "ok" and row.get("intervention_applications") != 1:
            raise ValueError("QCI audit active patch did not apply exactly once")
    candidate_ids = summary.get("candidate_ids")
    if not isinstance(candidate_ids, list) or not 1 <= len(candidate_ids) <= 8:
        raise ValueError("QCI audit candidate count is outside the frozen range")
    if set(str(item) for item in candidate_ids) != set(by_candidate):
        raise ValueError("QCI audit summary candidates differ from raw rows")
    expected_rows = len(candidate_ids) * 4 * len(EXPECTED_OPERATORS)
    if len(rows) != expected_rows or summary.get("candidate_execution_count") != expected_rows:
        raise ValueError("QCI audit candidate execution denominator differs")
    for candidate, candidate_rows in by_candidate.items():
        counts = Counter(str(row["operator"]) for row in candidate_rows)
        if set(counts) != EXPECTED_OPERATORS or any(counts[operator] != 4 for operator in EXPECTED_OPERATORS):
            raise ValueError(f"QCI audit operator denominator differs for {candidate}: {counts}")
    controls = json.loads((root / "message_positive_controls.json").read_text(encoding="utf-8"))
    if len(controls) != 8 or summary.get("message_positive_control_count") != 8:
        raise ValueError("QCI audit message-control denominator is not eight")
    if summary.get("development_audit_executions") != expected_rows + 8:
        raise ValueError("QCI audit total execution denominator differs")
    assessments = json.loads((root / "candidate_audit_assessments.json").read_text(encoding="utf-8"))
    if len(assessments) != len(candidate_ids) or {row["candidate_id"] for row in assessments} != set(by_candidate):
        raise ValueError("QCI audit assessments do not cover executed candidates")
    supported = sorted(str(row["candidate_id"]) for row in assessments if row.get("status") == "supported")
    if sorted(str(item) for item in summary.get("audit_supported_candidates", [])) != supported:
        raise ValueError("QCI audit support summary differs from assessments")
    expected_state = "READY_FOR_METHOD_FREEZE_REVIEW" if supported else "STOP_INTERNAL_CAUSAL_CLAIM"
    if summary.get("next_state") != expected_state:
        raise ValueError("QCI audit next state differs from support evidence")
    ledger = summary["query_ledger"]
    if ledger["executions"] != expected_rows + 8 or ledger["executions"] > ledger["maximum_executions"]:
        raise ValueError("QCI audit execution ledger differs")
    if ledger["forward_steps"] > ledger["maximum_forward_steps"]:
        raise ValueError("QCI audit forward-step budget was exceeded")
    return {
        "overall": "PASS",
        "run_id": summary["run_id"],
        "candidate_count": len(candidate_ids),
        "candidate_execution_count": len(rows),
        "message_positive_control_count": len(controls),
        "invalid_or_error_count": sum(row.get("status") != "ok" for row in rows),
        "audit_supported_candidates": supported,
        "next_gate": expected_state,
        "development_audit_executions": expected_rows + 8,
        "validation_executions": 0,
        "test_executions": 0,
    }


def main() -> None:
    """CLI entry point for downloaded QCI-A1 verification."""
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    arguments = parser.parse_args()
    print(json.dumps(verify_audit(arguments.root), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
