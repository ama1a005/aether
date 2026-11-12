"""Independently verify a downloaded QCI-1.1 result bundle."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import tarfile
from typing import Any


EXPECTED_OPERATORS = {
    "paired_rescue", "paired_induction", "shuffled_donor_rescue",
    "irrelevant_position_rescue", "identity_clean_to_clean",
    "identity_attacked_to_attacked", "passive_hook",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve(root: Path, recorded: str) -> Path:
    """Resolve a Kaggle-recorded artifact to its extracted local counterpart."""
    path = root / Path(recorded).name
    if path.is_file():
        return path
    matches = list(root.rglob(Path(recorded).name))
    if len(matches) != 1:
        raise ValueError(f"cannot uniquely resolve artifact: {recorded}")
    return matches[0]


def _verify_archive_contents(root: Path, entries: dict[str, str]) -> list[str]:
    """Verify retained archive entries, allowing only omitted execution logs.

    Atomic ingestion verifies the complete downloaded archive. Git deliberately
    excludes ``*.log`` files, so a later clean checkout contains the scientific
    artifacts and ingest receipt but not notebook console logs. No non-log
    artifact may be absent, and every retained file is still hash-verified.
    """
    omitted_logs: list[str] = []
    failures: list[str] = []
    for recorded, expected in entries.items():
        try:
            local = _resolve(root, recorded)
        except ValueError:
            if Path(recorded).suffix == ".log":
                omitted_logs.append(recorded)
                continue
            raise
        if _sha256(local) != expected:
            failures.append(recorded)
    if failures:
        raise ValueError(f"QCI archive-content hash failures: {failures}")
    return sorted(omitted_logs)


def verify(root: Path, archive: Path | None = None) -> dict[str, Any]:
    """Verify hashes, denominators, controls, budgets and split locks."""
    root = root.resolve()
    required = {
        "summary.json", "manifest.json", "raw_interventions.jsonl",
        "candidate_assessments.json", "message_positive_controls.json",
        "qci_preflight.json", "qci_model_access.json", "archive_contents.json",
    }
    missing = sorted(name for name in required if not (root / name).is_file())
    if missing:
        raise FileNotFoundError(f"QCI bundle is missing files: {missing}")
    summary = json.loads((root / "summary.json").read_text(encoding="utf-8"))
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    preflight = json.loads((root / "qci_preflight.json").read_text(encoding="utf-8"))
    marker = json.loads((root / "qci_model_access.json").read_text(encoding="utf-8"))
    if preflight["decision"]["overall"] != "PASS":
        raise ValueError("QCI preflight did not pass")
    if marker.get("state") != "QCI_DISCOVERY_COMPLETE":
        raise ValueError("QCI marker is not complete")
    if summary.get("development_audit_executions") != 0:
        raise ValueError("QCI bundle accessed development audit")
    if summary.get("validation_executions") != 0 or summary.get("test_executions") != 0:
        raise ValueError("QCI bundle accessed a locked split")
    manifest_failures = []
    for recorded, expected in manifest["artifact_paths"].items():
        local = _resolve(root, recorded)
        if _sha256(local) != expected:
            manifest_failures.append(recorded)
    if manifest_failures:
        raise ValueError(f"QCI manifest hash failures: {manifest_failures}")
    archive_contents = json.loads((root / "archive_contents.json").read_text(encoding="utf-8"))
    omitted_archive_logs = _verify_archive_contents(root, archive_contents)
    rows = [json.loads(line) for line in (root / "raw_interventions.jsonl").read_text(encoding="utf-8").splitlines() if line]
    if len(rows) != 1344 or summary.get("candidate_execution_count") != 1344:
        raise ValueError("QCI candidate execution denominator is not 1344")
    by_candidate: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_candidate[str(row["candidate_id"])].append(row)
        if row.get("hook_cleanup") is not True:
            raise ValueError("QCI row did not clean up hooks")
        if row["operator"] != "passive_hook" and row.get("status") == "ok" and row.get("intervention_applications") != 1:
            raise ValueError("QCI active patch did not apply exactly once")
    if len(by_candidate) != 12:
        raise ValueError("QCI bundle does not contain 12 region-qualified candidates")
    for candidate, candidate_rows in by_candidate.items():
        counts = Counter(str(row["operator"]) for row in candidate_rows)
        if set(counts) != EXPECTED_OPERATORS or any(counts[operator] != 16 for operator in EXPECTED_OPERATORS):
            raise ValueError(f"QCI operator denominator differs for {candidate}: {counts}")
    controls = json.loads((root / "message_positive_controls.json").read_text(encoding="utf-8"))
    if len(controls) != 32 or summary.get("message_positive_control_count") != 32:
        raise ValueError("QCI message-control denominator is not 32")
    assessments = json.loads((root / "candidate_assessments.json").read_text(encoding="utf-8"))
    if len(assessments) != 12 or {row["candidate_id"] for row in assessments} != set(by_candidate):
        raise ValueError("QCI candidate assessments do not cover the executed candidates")
    supported_from_assessments = sorted(
        str(row["candidate_id"]) for row in assessments if row.get("status") == "supported"
    )
    supported_from_summary = summary.get("supported_candidates")
    if not isinstance(supported_from_summary, list):
        raise ValueError("QCI summary supported_candidates is not a list")
    if sorted(str(candidate) for candidate in supported_from_summary) != supported_from_assessments:
        raise ValueError("QCI summary support classification differs from candidate assessments")
    expected_outcome = (
        "supported_candidates_found" if supported_from_assessments
        else "no_internal_candidate_passed"
    )
    if summary.get("assessment_outcome") != expected_outcome:
        raise ValueError("QCI assessment outcome differs from frozen support classification")
    ledger = summary["query_ledger"]
    if ledger["executions"] != 1376 or ledger["executions"] > ledger["maximum_executions"]:
        raise ValueError("QCI execution ledger is invalid")
    if ledger["forward_steps"] > ledger["maximum_forward_steps"]:
        raise ValueError("QCI forward-step budget was exceeded")
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
                    raise ValueError(f"unsafe QCI archive member: {member.name}")
            archive_entries = len(members)
    return {
        "overall": "PASS", "run_id": summary["run_id"],
        "candidate_execution_count": len(rows), "candidate_count": len(by_candidate),
        "message_positive_control_count": len(controls),
        "invalid_or_error_count": sum(row.get("status") != "ok" for row in rows),
        "supported_candidates": supported_from_assessments,
        "next_gate": (
            "ELIGIBLE_TO_FREEZE_DEVELOPMENT_AUDIT"
            if supported_from_assessments else "STOP_NO_SUPPORTED_CANDIDATE"
        ),
        "development_audit_executions": 0, "validation_executions": 0, "test_executions": 0,
        "manifest_entry_count": len(manifest["artifact_paths"]),
        "archive_content_entry_count": len(archive_contents),
        "omitted_gitignored_log_count": len(omitted_archive_logs),
        "omitted_gitignored_logs": omitted_archive_logs,
        "archive_sha256": archive_hash, "archive_entry_count": archive_entries,
    }


def main() -> None:
    """CLI entry point for downloaded QCI verification."""
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--archive", type=Path)
    arguments = parser.parse_args()
    print(json.dumps(verify(arguments.root, arguments.archive), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
