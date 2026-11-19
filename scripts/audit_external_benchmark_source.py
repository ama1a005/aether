"""Create a machine-readable, non-redistributive audit of a pinned benchmark source."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any


SPECS = {
    "mcptox": {
        "repository": "https://github.com/zhiqiangwang4/MCPTox-Benchmark",
        "commit": "f85189f9ad12504c197c7f920ab818a40657b1fa",
        "data_files": ("pure_tool.json", "response_all.json"),
        "license_files": (),
        "native_entrypoints": ("analysis.ipynb",),
        "expected_state": "BLOCKED_LICENSE_AND_NO_NATIVE_EVALUATOR",
    },
    "tamas": {
        "repository": "https://github.com/microsoft/TAMAS",
        "commit": "545c112af9aab93b7ef2b0b60831d93c81c365c3",
        "data_files": (),
        "license_files": ("LICENSE", "LICENSE.CDLA-2.0"),
        "native_entrypoints": ("autogen_inference.py", "crewai_inference.py", "eval"),
        "expected_state": "BLOCKED_NATIVE_FRAMEWORK_OR_PROVIDER",
    },
}


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git(source: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=source, check=True, capture_output=True, text=True).stdout.strip()


def audit(kind: str, source: Path) -> dict[str, Any]:
    """Audit an exact checkout and return metadata without reading records into output."""
    spec = SPECS[kind]
    source = source.resolve()
    if not source.is_dir():
        raise FileNotFoundError(source)
    commit = _git(source, "rev-parse", "HEAD")
    if commit != spec["commit"]:
        raise ValueError(f"expected {spec['commit']}, found {commit}")
    if _git(source, "status", "--porcelain"):
        raise ValueError("upstream checkout is dirty")
    license_paths = [path for path in spec["license_files"] if (source / path).is_file()]
    data_files = [path for path in spec["data_files"] if (source / path).is_file()]
    if kind == "tamas":
        data_files = [path.relative_to(source).as_posix() for path in sorted((source / "data").rglob("*.json"))]
    return {
        "schema_version": "aether.external-source-audit.v1",
        "benchmark": kind.upper() if kind == "tamas" else "MCPTox",
        "repository": spec["repository"], "commit": commit,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_path": str(source), "git_clean": True,
        "license": {"paths": license_paths, "sha256": {path: _hash(source / path) for path in license_paths},
                    "status": "PRESENT" if license_paths else "ABSENT"},
        "data_inventory": {"paths": data_files, "count": len(data_files),
                           "sha256": {path: _hash(source / path) for path in data_files}},
        "native_entrypoints": list(spec["native_entrypoints"]),
        "native_entrypoints_present": {path: (source / path).exists() for path in spec["native_entrypoints"]},
        "execution_state": spec["expected_state"],
        "raw_data_redistributed": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=sorted(SPECS))
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = audit(args.kind, args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
