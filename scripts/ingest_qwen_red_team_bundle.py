"""Verify and atomically ingest a real-Qwen red-team evidence bundle."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from experiments.external_bundle import ingest_bundle
from scripts.verify_qwen_red_team_bundle import verify


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    report = verify(args.source)
    result = ingest_bundle(args.source, args.destination, expected_kind="qwen_red_team")
    print(json.dumps({"verification": report, "ingest": result.__dict__}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
