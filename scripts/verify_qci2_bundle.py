"""Independently verify a downloaded QCI-2 decision-semantic bundle."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import tarfile
from typing import Any

from causal.qci2_execution import assess_semantic_candidate
from scripts.verify_qci_bundle import _resolve, _sha256


EXPECTED_OPERATORS = {
    "paired_rescue", "paired_induction",
    "same_decision_rescue", "same_decision_induction",
    "opposite_decision_rescue", "opposite_decision_induction",
    "irrelevant_position_rescue", "identity_clean_to_clean",
    "identity_attacked_to_attacked", "passive_hook",
}
EXPECTED_THRESHOLDS = {
    "median_effect_min": 0.5,
    "consistency_min": 0.75,
    "same_decision_gap_max": 0.1,
    "opposite_decision_contrast_min": 0.2,
    "position_contrast_min": 0.2,
}


def verify(root: Path, archive: Path | None = None) -> dict[str, Any]:
    """Verify QCI-2 hashes, classifications, denominators, budgets and split locks."""
    root = root.resolve()
    required = {
        "summary.json", "manifest.json", "raw_interventions.jsonl",
        "candidate_assessments.json", "message_positive_controls.json",
        "qci2_preflight.json", "qci2_model_access.json", "archive_contents.json",
    }
    missing = sorted(name for name in required if not (root / name).is_file())
    if missing:
        raise FileNotFoundError(f"QCI-2 bundle is missing files: {missing}")
    summary = json.loads((root / "summary.json").read_text(encoding="utf-8"))
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    preflight = json.loads((root / "qci2_preflight.json").read_text(encoding="utf-8"))
    marker = json.loads((root / "qci2_model_access.json").read_text(encoding="utf-8"))
    if preflight["decision"]["overall"] != "PASS":
        raise ValueError("QCI-2 preflight did not pass")
    if marker.get("state") != "QCI2_DISCOVERY_COMPLETE":
        raise ValueError("QCI-2 marker is not complete")
    if summary.get("development_audit_executions") != 0:
        raise ValueError("QCI-2 bundle accessed development audit")
    if summary.get("validation_executions") != 0 or summary.get("test_executions") != 0:
        raise ValueError("QCI-2 bundle accessed a locked split")
    failures = []
    for recorded, expected in manifest["artifact_paths"].items():
        if _sha256(_resolve(root, recorded)) != expected:
            failures.append(recorded)
    if failures:
        raise ValueError(f"QCI-2 manifest hash failures: {failures}")
    archive_contents = json.loads((root / "archive_contents.json").read_text(encoding="utf-8"))
    failures = []
    for recorded, expected in archive_contents.items():
        if _sha256(_resolve(root, recorded)) != expected:
            failures.append(recorded)
    if failures:
        raise ValueError(f"QCI-2 archive-content hash failures: {failures}")

    rows = [json.loads(line) for line in (root / "raw_interventions.jsonl").read_text(encoding="utf-8").splitlines() if line]
    if len(rows) != 1920 or summary.get("candidate_execution_count") != 1920:
        raise ValueError("QCI-2 candidate execution denominator is not 1920")
    by_candidate: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_candidate[str(row["candidate_id"])].append(row)
        if row.get("hook_cleanup") is not True:
            raise ValueError("QCI-2 row did not clean up hooks")
        if row["operator"] != "passive_hook" and row.get("status") == "ok" and row.get("intervention_applications") != 1:
            raise ValueError("QCI-2 active patch did not apply exactly once")
    if len(by_candidate) != 12:
        raise ValueError("QCI-2 bundle does not contain the 12 retained candidates")
    for candidate, candidate_rows in by_candidate.items():
        counts = Counter(str(row["operator"]) for row in candidate_rows)
        if set(counts) != EXPECTED_OPERATORS or any(counts[name] != 16 for name in EXPECTED_OPERATORS):
            raise ValueError(f"QCI-2 operator denominator differs for {candidate}: {counts}")

    controls = json.loads((root / "message_positive_controls.json").read_text(encoding="utf-8"))
    if len(controls) != 32 or summary.get("message_positive_control_count") != 32:
        raise ValueError("QCI-2 message-control denominator is not 32")
    assessments = json.loads((root / "candidate_assessments.json").read_text(encoding="utf-8"))
    recorded = {str(row["candidate_id"]): row for row in assessments}
    if len(recorded) != 12 or set(recorded) != set(by_candidate):
        raise ValueError("QCI-2 assessments do not cover the executed candidates")
    recalculated = {
        candidate: assess_semantic_candidate(candidate_rows, EXPECTED_THRESHOLDS)
        for candidate, candidate_rows in by_candidate.items()
    }
    if recalculated != recorded:
        raise ValueError("QCI-2 recorded assessments differ from independent recalculation")
    supported = sorted(candidate for candidate, row in recalculated.items() if row["status"] == "supported")
    if sorted(str(candidate) for candidate in summary.get("supported_candidates", [])) != supported:
        raise ValueError("QCI-2 summary support differs from independent classification")
    outcome = "supported_candidates_found" if supported else "no_semantic_candidate_passed"
    if summary.get("assessment_outcome") != outcome:
        raise ValueError("QCI-2 assessment outcome differs from independent classification")
    ledger = summary["query_ledger"]
    if ledger["executions"] != 1952 or ledger["executions"] > ledger["maximum_executions"]:
        raise ValueError("QCI-2 execution ledger is invalid")
    if ledger["forward_steps"] > ledger["maximum_forward_steps"]:
        raise ValueError("QCI-2 forward-step budget was exceeded")

    archive_hash = None
    archive_entries = None
    if archive is not None:
        archive = archive.resolve()
        archive_hash = _sha256(archive)
        with tarfile.open(archive, "r:gz") as bundle:
            members = bundle.getmembers()
            for member in members:
                parts = Path(member.name).parts
                if Path(member.name).is_absolute() or ".." in parts:
                    raise ValueError(f"unsafe QCI-2 archive member: {member.name}")
            archive_entries = len(members)
    return {
        "overall": "PASS", "run_id": summary["run_id"],
        "candidate_execution_count": len(rows), "candidate_count": len(by_candidate),
        "message_positive_control_count": len(controls),
        "invalid_or_error_count": sum(row.get("status") != "ok" for row in rows),
        "supported_candidates": supported,
        "next_gate": (
            "ELIGIBLE_TO_FREEZE_QCI2_DEVELOPMENT_AUDIT"
            if supported else "STOP_DECISION_SEMANTIC_CLAIM"
        ),
        "next_gate": "ELIGIBLE_TO_FREEZE_QCI2_DEVELOPMENT_AUDIT" if supported else "STOP_DECISION_SEMANTIC_CLAIM",
        "development_audit_executions": 0, "validation_executions": 0, "test_executions": 0,
        "manifest_entry_count": len(manifest["artifact_paths"]),
        "archive_content_entry_count": len(archive_contents),
        "archive_sha256": archive_hash, "archive_entry_count": archive_entries,
    }


def main() -> None:
    """Run QCI-2 verification from the command line."""
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--archive", type=Path)
    arguments = parser.parse_args()
    print(json.dumps(verify(arguments.root, arguments.archive), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
