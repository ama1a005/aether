"""Verify an AETHER external experiment bundle without modifying the repository."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from dataclasses import asdict
from experiments.external_bundle import verify_bundle


def main() -> None:
    """Parse CLI arguments and print the verified bundle identity."""
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--expected-kind")
    arguments = parser.parse_args()
    print(json.dumps(asdict(verify_bundle(arguments.root, expected_kind=arguments.expected_kind)), indent=2))


if __name__ == "__main__":
    main()
