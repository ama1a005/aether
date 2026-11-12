"""Independently verify a QCI-2A1 semantic development-audit bundle."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
from typing import Any

from causal.qci2_execution import assess_semantic_candidate
from scripts.verify_qci2_bundle import EXPECTED_OPERATORS, EXPECTED_THRESHOLDS
from scripts.verify_qci_bundle import _resolve, _sha256, _verify_archive_contents


def verify_audit(root: Path) -> dict[str, Any]:
    """Verify QCI-2A1 hashes, classifications, budgets and split locks."""
    root = root.resolve()
    required = {"summary.json", "manifest.json", "raw_audit_interventions.jsonl",
                "candidate_audit_assessments.json", "message_positive_controls.json",
                "audit_preflight.json", "audit_model_access.json", "archive_contents.json"}
    missing = sorted(name for name in required if not (root / name).is_file())
    if missing:
        raise FileNotFoundError(f"QCI-2 audit bundle is missing files: {missing}")
    summary = json.loads((root / "summary.json").read_text(encoding="utf-8"))
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    preflight = json.loads((root / "audit_preflight.json").read_text(encoding="utf-8"))
    marker = json.loads((root / "audit_model_access.json").read_text(encoding="utf-8"))
    if preflight["decision"]["overall"] != "PASS" or marker.get("state") != "QCI2_AUDIT_COMPLETE":
        raise ValueError("QCI-2 audit preflight or completion marker failed")
    if summary.get("validation_executions") != 0 or summary.get("test_executions") != 0:
        raise ValueError("QCI-2 audit accessed a locked split")
    failures = [recorded for recorded, expected in manifest["artifact_paths"].items()
                if _sha256(_resolve(root, recorded)) != expected]
    if failures:
        raise ValueError(f"QCI-2 audit manifest hash failures: {failures}")
    inventory = json.loads((root / "archive_contents.json").read_text(encoding="utf-8"))
    omitted_logs = _verify_archive_contents(root, inventory)
    rows = [json.loads(line) for line in (root / "raw_audit_interventions.jsonl").read_text(encoding="utf-8").splitlines() if line]
    by_candidate: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_candidate[str(row["candidate_id"])].append(row)
        if row.get("hook_cleanup") is not True:
            raise ValueError("QCI-2 audit row did not clean up hooks")
        if row["operator"] != "passive_hook" and row.get("status") == "ok" and row.get("intervention_applications") != 1:
            raise ValueError("QCI-2 audit active patch did not apply exactly once")
    candidate_ids = summary.get("candidate_ids")
    if not isinstance(candidate_ids, list) or not 1 <= len(candidate_ids) <= 12 or set(candidate_ids) != set(by_candidate):
        raise ValueError("QCI-2 audit candidate set is invalid")
    expected_rows = len(candidate_ids) * 4 * len(EXPECTED_OPERATORS)
    if len(rows) != expected_rows or summary.get("candidate_execution_count") != expected_rows:
        raise ValueError("QCI-2 audit execution denominator differs")
    for candidate, candidate_rows in by_candidate.items():
        counts = Counter(str(row["operator"]) for row in candidate_rows)
        if set(counts) != EXPECTED_OPERATORS or any(counts[name] != 4 for name in EXPECTED_OPERATORS):
            raise ValueError(f"QCI-2 audit operator denominator differs for {candidate}")
    controls = json.loads((root / "message_positive_controls.json").read_text(encoding="utf-8"))
    if len(controls) != 8 or summary.get("message_positive_control_count") != 8:
        raise ValueError("QCI-2 audit message-control denominator differs")
    assessments = json.loads((root / "candidate_audit_assessments.json").read_text(encoding="utf-8"))
    recorded = {str(row["candidate_id"]): row for row in assessments}
    recalculated = {candidate: assess_semantic_candidate(candidate_rows, EXPECTED_THRESHOLDS, expected_count=4)
                    for candidate, candidate_rows in by_candidate.items()}
    if recorded != recalculated:
        raise ValueError("QCI-2 audit assessments differ from independent recalculation")
    supported = sorted(candidate for candidate, row in recalculated.items() if row["status"] == "supported")
    if sorted(summary.get("audit_supported_candidates", [])) != supported:
        raise ValueError("QCI-2 audit support summary differs")
    state = "READY_FOR_METHOD_FREEZE_REVIEW" if supported else "STOP_DECISION_SEMANTIC_CLAIM"
    if summary.get("next_state") != state:
        raise ValueError("QCI-2 audit next state differs")
    ledger = summary["query_ledger"]
    total = expected_rows + 8
    if summary.get("development_audit_executions") != total or ledger["executions"] != total or ledger["executions"] > ledger["maximum_executions"]:
        raise ValueError("QCI-2 audit ledger differs")
    if ledger["forward_steps"] > ledger["maximum_forward_steps"]:
        raise ValueError("QCI-2 audit forward budget exceeded")
    return {"overall": "PASS", "run_id": summary["run_id"], "candidate_count": len(candidate_ids),
            "candidate_execution_count": len(rows), "message_positive_control_count": 8,
            "invalid_or_error_count": sum(row.get("status") != "ok" for row in rows),
            "audit_supported_candidates": supported, "next_gate": state,
            "development_audit_executions": total, "validation_executions": 0, "test_executions": 0,
            "omitted_gitignored_logs": omitted_logs}


def main() -> None:
    """Run strict QCI-2A1 verification."""
    parser = argparse.ArgumentParser(); parser.add_argument("root", type=Path)
    print(json.dumps(verify_audit(parser.parse_args().root), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
