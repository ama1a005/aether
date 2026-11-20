"""Atomically ingest an independently verified real-Qwen Agent C bundle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import tempfile

from scripts.verify_qwen_agent_c_real_bundle import verify


def ingest(source: Path, destination: Path) -> Path:
    """Verify, stage, reverify and refuse destination overwrite."""
    source = source.resolve(); destination = destination.resolve(); verified = verify(source)
    if destination.exists():
        raise FileExistsError(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f".{destination.name}-", dir=destination.parent) as temporary:
        staged = Path(temporary) / destination.name; shutil.copytree(source, staged); verify(staged)
        staged.replace(destination)
    receipt = destination.parent / f"{destination.name}.ingest_receipt.json"
    receipt.write_text(json.dumps({"schema_version": "aether.qwen-agent-c-real-ingest.v1",
                                   **verified}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return destination


def main() -> None:
    """Ingest one verified bundle."""
    parser = argparse.ArgumentParser(); parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path); args = parser.parse_args()
    print(ingest(args.source, args.destination))


if __name__ == "__main__":
    main()
