"""Atomically ingest an independently verified external experiment bundle."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from experiments.external_bundle import ingest_bundle


def main() -> None:
    """Verify and copy a bundle to a new evidence destination."""
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--expected-kind")
    arguments = parser.parse_args()
    result = ingest_bundle(arguments.source, arguments.destination, expected_kind=arguments.expected_kind)
    print(json.dumps(asdict(result), indent=2))


if __name__ == "__main__":
    main()
