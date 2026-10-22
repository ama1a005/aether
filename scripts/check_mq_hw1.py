"""Measure the frozen MQ-HW1 resource gate without accessing any model files."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys

import psutil

from experiments.manifest import sha256_file
from paired_trace.model_qualification import evaluate_mq_hw1

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GATE = ROOT / "configs/model_qualification/v2_mq_hw1.json"


def measure(gate_path: Path, cache_drive: Path) -> dict[str, object]:
    """Return physical-memory/disk measurements and the frozen gate decision."""
    gate_path = gate_path.resolve()
    cache_drive = cache_drive.resolve()
    memory = psutil.virtual_memory()
    disk = shutil.disk_usage(cache_drive)
    values = {
        "installed_ram_gib": memory.total / 2**30,
        "available_ram_gib": memory.available / 2**30,
        "disk_free_gib": disk.free / 2**30,
    }
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    return {
        "schema_version": "aether.mq-hw1-preflight.v1",
        "utc_timestamp": datetime.now(timezone.utc).isoformat(),
        "python_executable": sys.executable,
        "gate_path": str(gate_path),
        "gate_sha256": sha256_file(gate_path),
        "cache_drive": str(cache_drive),
        "model_accessed": False,
        "measurements": values,
        "decision": evaluate_mq_hw1(values, gate),
    }


def main() -> None:
    """Print the decision, optionally persist it, and fail when model access is blocked."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gate", type=Path, default=DEFAULT_GATE)
    parser.add_argument("--cache-drive", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = measure(args.gate, args.cache_drive)
    payload = json.dumps(result, indent=2)
    print(payload)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    if result["decision"]["overall"] != "PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
