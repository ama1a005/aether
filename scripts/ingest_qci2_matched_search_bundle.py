"""Atomically ingest an independently verified CORE-02 bundle."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import tempfile

from scripts.verify_qci2_matched_search_bundle import _hash, verify


def ingest(source: Path, destination: Path) -> dict[str, object]:
    """Verify and copy a new immutable evidence directory without overwriting."""
    source, destination = source.resolve(), destination.resolve()
    if destination.exists():
        raise FileExistsError(f"CORE-02 destination exists: {destination}")
    report = verify(source)
    files = sorted(path for path in source.rglob("*") if path.is_file())
    if any(path.is_symlink() for path in files):
        raise ValueError("CORE-02 source contains symlinks")
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}-", dir=destination.parent))
    try:
        hashes = {}
        for path in files:
            relative = path.relative_to(source)
            target = staging / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            hashes[relative.as_posix()] = _hash(target)
        receipt = {"schema_version": "aether.core02-ingest.v1",
                   "ingested_utc": datetime.now(timezone.utc).isoformat(),
                   "verification": report, "copied_artifact_sha256": hashes}
        (staging / "ingest_receipt.json").write_text(
            json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8"
        )
        staging.replace(destination)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    print(json.dumps(ingest(args.source, args.destination), indent=2))


if __name__ == "__main__":
    main()
