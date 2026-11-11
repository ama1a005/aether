"""Verify and atomically ingest a completed QCI-1.1 evidence bundle."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import tempfile
from typing import Any

from scripts.verify_qci_bundle import _sha256, verify


REQUIRED_TOP_LEVEL = {
    "summary.json",
    "manifest.json",
    "raw_interventions.jsonl",
    "candidate_assessments.json",
    "message_positive_controls.json",
    "qci_preflight.json",
    "qci_model_access.json",
    "archive_contents.json",
}


def _bundle_files(source: Path) -> list[Path]:
    """Return regular, non-symlink bundle files with unambiguous basenames."""
    files = sorted(path for path in source.rglob("*") if path.is_file())
    symlinks = [path for path in files if path.is_symlink()]
    if symlinks:
        raise ValueError(f"QCI bundle contains symlinks: {symlinks}")
    by_name: dict[str, list[Path]] = {}
    for path in files:
        by_name.setdefault(path.name, []).append(path)
    duplicates = {name: paths for name, paths in by_name.items() if len(paths) != 1}
    if duplicates:
        raise ValueError(f"QCI bundle contains duplicate artifact names: {sorted(duplicates)}")
    missing = REQUIRED_TOP_LEVEL - set(by_name)
    if missing:
        raise FileNotFoundError(f"QCI bundle is missing required artifacts: {sorted(missing)}")
    return files


def ingest(source: Path, destination: Path, archive: Path | None = None) -> dict[str, Any]:
    """Verify `source`, copy it into a new destination, and write an ingest receipt."""
    source = source.resolve()
    destination = destination.resolve()
    if destination.exists():
        raise FileExistsError(f"QCI ingest destination already exists: {destination}")
    report = verify(source, archive)
    files = _bundle_files(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}-", dir=destination.parent))
    try:
        copied: dict[str, str] = {}
        for path in files:
            target = staging / path.name
            shutil.copy2(path, target)
            copied[path.name] = _sha256(target)
        receipt = {
            "schema_version": "aether.qci-ingest.v1",
            "ingested_utc": datetime.now(timezone.utc).isoformat(),
            "source": str(source),
            "archive": str(archive.resolve()) if archive is not None else None,
            "verification": report,
            "copied_artifact_sha256": copied,
        }
        (staging / "ingest_receipt.json").write_text(
            json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8"
        )
        staging.replace(destination)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return receipt


def main() -> None:
    """Run strict QCI bundle ingestion from the command line."""
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--archive", type=Path)
    arguments = parser.parse_args()
    print(json.dumps(ingest(arguments.source, arguments.destination, arguments.archive), indent=2))


if __name__ == "__main__":
    main()
