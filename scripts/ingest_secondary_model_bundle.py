"""Atomically ingest an independently verified second-model bundle."""
from __future__ import annotations
import argparse, json, shutil, uuid
from pathlib import Path
from scripts.verify_secondary_model_bundle import verify

ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / "results/phase1/model_qualification/second_model"

def ingest(source: Path, destination: Path = DESTINATION) -> dict:
    """Verify, stage and promote without overwriting evidence."""
    receipt = verify(source)
    if destination.exists(): raise FileExistsError(f"destination exists: {destination}")
    staging = destination.parent / f".{destination.name}.staging-{uuid.uuid4().hex}"
    staging.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copytree(source, staging, symlinks=False); verify(staging); staging.replace(destination)
    finally:
        if staging.exists(): shutil.rmtree(staging)
    (destination / "ingestion_receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8")
    return receipt

def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(); parser.add_argument("source", type=Path); parser.add_argument("--destination", type=Path, default=DESTINATION)
    args = parser.parse_args(); print(json.dumps(ingest(args.source, args.destination), indent=2))
if __name__ == "__main__": main()
