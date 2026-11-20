"""Atomically ingest an independently verified Qwen SAE result bundle."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import tempfile
from typing import Any

from experiments.phase1.qwen_sae_training import sha256_file
from scripts.verify_qwen_sae_bundle import verify


def ingest(source: Path, destination: Path) -> dict[str, Any]:
    """Verify, copy without overwrite, and expose the canonical gate summary."""
    source, destination = source.resolve(), destination.resolve()
    if destination.exists():
        raise FileExistsError(f"Qwen SAE destination exists: {destination}")
    report = verify(source)
    files = sorted(path for path in source.rglob("*") if path.is_file())
    if any(path.is_symlink() for path in files):
        raise ValueError("Qwen SAE source contains symlinks")
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}-", dir=destination.parent))
    try:
        hashes: dict[str, str] = {}
        for path in files:
            relative = path.relative_to(source)
            target = staging / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            hashes[relative.as_posix()] = sha256_file(target)
        final_summary = staging / "final/summary.json"
        if not final_summary.is_file():
            raise FileNotFoundError("verified Qwen SAE bundle lacks final summary")
        shutil.copy2(final_summary, staging / "summary.json")
        receipt = {
            "schema_version": "aether.qwen-sae-ingest.v1",
            "ingested_utc": datetime.now(timezone.utc).isoformat(),
            "verification": report,
            "copied_artifact_sha256": hashes,
            "canonical_summary_sha256": sha256_file(staging / "summary.json"),
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
    """Verify and ingest a retained Qwen SAE bundle."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    print(json.dumps(ingest(args.source, args.destination), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
