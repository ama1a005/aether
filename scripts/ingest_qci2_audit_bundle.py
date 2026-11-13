"""Verify and atomically ingest a completed QCI-2A1 audit bundle."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import tempfile
from typing import Any

from scripts.verify_qci_bundle import _sha256
from scripts.verify_qci2_audit_bundle import verify_audit


REQUIRED = {
    "summary.json", "manifest.json", "raw_audit_interventions.jsonl",
    "candidate_audit_assessments.json", "message_positive_controls.json",
    "audit_preflight.json", "audit_model_access.json", "archive_contents.json",
}


def ingest(source: Path, destination: Path, archive: Path | None = None) -> dict[str, Any]:
    """Verify `source`, copy it into a new destination, and record provenance."""
    source, destination = source.resolve(), destination.resolve()
    if destination.exists():
        raise FileExistsError(f"QCI-2 audit destination already exists: {destination}")
    report = verify_audit(source)
    files = sorted(path for path in source.rglob("*") if path.is_file())
    if any(path.is_symlink() for path in files):
        raise ValueError("QCI-2 audit bundle contains symlinks")
    names: dict[str, list[Path]] = {}
    for path in files:
        names.setdefault(path.name, []).append(path)
    duplicates = sorted(name for name, paths in names.items() if len(paths) != 1)
    if duplicates:
        raise ValueError(f"QCI-2 audit bundle has duplicate artifact names: {duplicates}")
    missing = sorted(REQUIRED - set(names))
    if missing:
        raise FileNotFoundError(f"QCI-2 audit bundle is missing artifacts: {missing}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}-", dir=destination.parent))
    try:
        copied: dict[str, str] = {}
        for path in files:
            target = staging / path.name
            shutil.copy2(path, target)
            copied[path.name] = _sha256(target)
        receipt = {
            "schema_version": "aether.qci2-audit-ingest.v1",
            "ingested_utc": datetime.now(timezone.utc).isoformat(),
            "source": str(source), "archive": str(archive.resolve()) if archive else None,
            "archive_sha256": _sha256(archive.resolve()) if archive else None,
            "verification": report, "copied_artifact_sha256": copied,
        }
        with (staging / "ingest_receipt.json").open(
                "w", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(receipt, indent=2, sort_keys=True))
        staging.replace(destination)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return receipt


def main() -> None:
    """Run strict QCI-2A1 ingestion."""
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path); parser.add_argument("destination", type=Path)
    parser.add_argument("--archive", type=Path)
    args = parser.parse_args()
    print(json.dumps(ingest(args.source, args.destination, args.archive), indent=2))


if __name__ == "__main__":
    main()
