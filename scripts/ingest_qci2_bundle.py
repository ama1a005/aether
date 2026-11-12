"""Verify and atomically ingest a completed QCI-2 evidence bundle."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import tempfile
from typing import Any

from scripts.verify_qci_bundle import _sha256
from scripts.verify_qci2_bundle import verify


REQUIRED = {
    "summary.json", "manifest.json", "raw_interventions.jsonl",
    "candidate_assessments.json", "message_positive_controls.json",
    "qci2_preflight.json", "qci2_model_access.json", "archive_contents.json",
}


def _files(source: Path) -> list[Path]:
    """Return non-symlink files after rejecting ambiguous artifact names."""
    files = sorted(path for path in source.rglob("*") if path.is_file())
    if any(path.is_symlink() for path in files):
        raise ValueError("QCI-2 bundle contains symlinks")
    names: dict[str, list[Path]] = {}
    for path in files:
        names.setdefault(path.name, []).append(path)
    duplicates = sorted(name for name, paths in names.items() if len(paths) != 1)
    if duplicates:
        raise ValueError(f"QCI-2 bundle contains duplicate artifact names: {duplicates}")
    missing = sorted(REQUIRED - set(names))
    if missing:
        raise FileNotFoundError(f"QCI-2 bundle is missing required artifacts: {missing}")
    return files


def ingest(source: Path, destination: Path, archive: Path | None = None) -> dict[str, Any]:
    """Verify, copy into a new destination, and record a QCI-2 receipt."""
    source = source.resolve()
    destination = destination.resolve()
    if destination.exists():
        raise FileExistsError(f"QCI-2 ingest destination already exists: {destination}")
    report = verify(source, archive)
    files = _files(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}-", dir=destination.parent))
    try:
        copied: dict[str, str] = {}
        for path in files:
            target = staging / path.name
            shutil.copy2(path, target)
            copied[path.name] = _sha256(target)
        receipt = {
            "schema_version": "aether.qci2-ingest.v1",
            "ingested_utc": datetime.now(timezone.utc).isoformat(),
            "source": str(source), "archive": str(archive.resolve()) if archive else None,
            "verification": report, "copied_artifact_sha256": copied,
        }
        (staging / "ingest_receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8")
        staging.replace(destination)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return receipt


def main() -> None:
    """Run strict QCI-2 ingestion from the command line."""
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--archive", type=Path)
    arguments = parser.parse_args()
    print(json.dumps(ingest(arguments.source, arguments.destination, arguments.archive), indent=2))


if __name__ == "__main__":
    main()
