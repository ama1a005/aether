"""Atomically ingest an independently verified CORE-05 test bundle."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import tempfile

from causal.remediation_freeze import sha256_file
from scripts.verify_core05_test_bundle import verify


def ingest(source: Path, destination: Path) -> dict[str, object]:
    """Verify and atomically copy CORE-05 without overwriting evidence."""
    source, destination = source.resolve(), destination.resolve()
    if destination.exists():
        raise FileExistsError(f"CORE-05 destination exists: {destination}")
    report = verify(source); files = sorted(path for path in source.rglob("*") if path.is_file())
    if any(path.is_symlink() for path in files):
        raise ValueError("CORE-05 source contains symlinks")
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}-", dir=destination.parent))
    try:
        hashes = {}
        for path in files:
            relative = path.relative_to(source); target = staging / relative
            target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(path, target)
            hashes[relative.as_posix()] = sha256_file(target)
        receipt = {"schema_version": "aether.core05-ingest.v1", "ingested_utc": datetime.now(timezone.utc).isoformat(),
                   "verification": report, "copied_artifact_sha256": hashes}
        (staging / "ingest_receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8")
        staging.replace(destination)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True); raise
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("source", type=Path); parser.add_argument("destination", type=Path)
    args = parser.parse_args(); print(json.dumps(ingest(args.source, args.destination), indent=2))


if __name__ == "__main__":
    main()
