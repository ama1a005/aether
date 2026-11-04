"""Fail-closed larger-machine preflight; this command never loads a model."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from importlib.metadata import PackageNotFoundError, version
import json
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

import psutil
import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs/transfer/phase1_larger_machine.yaml"


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect(config_path: Path) -> dict[str, Any]:
    """Inspect runtime, resources, packages, cache and outputs without model access."""
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    memory = psutil.virtual_memory()
    disk = shutil.disk_usage(ROOT)
    checks: dict[str, Any] = {}
    checks["python_3_11"] = sys.version_info[:2] == (3, 11)
    checks["installed_ram"] = memory.total / 2**30 >= config["minimum_ram_gib"]
    checks["available_ram"] = memory.available / 2**30 >= config["minimum_available_ram_gib"]
    checks["disk"] = disk.free / 2**30 >= config["minimum_disk_free_gib"]
    packages = {}
    for package, expected in config["packages"].items():
        try:
            actual = version(package)
        except PackageNotFoundError:
            actual = None
        packages[package] = {"expected": str(expected), "actual": actual,
                             "pass": actual == str(expected)}
    checks["packages"] = all(item["pass"] for item in packages.values())
    lock_files = {}
    for relative, expected_hash in config.get("lock_files", {}).items():
        lock_path = ROOT / relative
        actual_hash = _hash(lock_path) if lock_path.is_file() else None
        lock_files[relative] = {"expected_sha256": expected_hash,
                                "actual_sha256": actual_hash,
                                "pass": actual_hash == expected_hash}
    checks["lock_files"] = all(item["pass"] for item in lock_files.values())
    cuda = {"visible": False, "detail": "nvidia-smi unavailable"}
    try:
        result = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,memory.free",
                                "--format=csv,noheader,nounits"], capture_output=True,
                                text=True, timeout=10, check=False)
        cuda = {"visible": result.returncode == 0, "detail": result.stdout.strip() or result.stderr.strip()}
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        cuda["detail"] = type(exc).__name__
    checks["cuda"] = cuda["visible"] if config["require_cuda"] else True
    cache = ROOT / config["model"]["cache_path"]
    revision_file = cache / "revision.json"
    cache_revision = None
    if revision_file.is_file():
        cache_revision = json.loads(revision_file.read_text(encoding="utf-8")).get("revision")
    checks["model_revision_pinned"] = config["model"]["revision"] not in {"", "pending", None}
    checks["cache"] = cache.is_dir() and cache_revision == config["model"]["revision"]
    outputs = []
    for relative in config["output_directories"]:
        path = ROOT / relative
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".aether_write_probe"
        try:
            probe.write_text("ok", encoding="utf-8")
            writable = True
        finally:
            probe.unlink(missing_ok=True)
        outputs.append({"path": str(path), "writable": writable})
    checks["outputs"] = all(item["writable"] for item in outputs)
    return {"schema_version": 1, "utc_timestamp": datetime.now(timezone.utc).isoformat(),
            "model_accessed": False, "python": sys.version, "python_executable": sys.executable,
            "config_sha256": _hash(config_path), "lock_files": lock_files, "measurements": {
                "ram_total_gib": memory.total / 2**30, "ram_available_gib": memory.available / 2**30,
                "disk_free_gib": disk.free / 2**30}, "cuda": cuda, "packages": packages,
            "model": {**config["model"], "cache_revision": cache_revision}, "outputs": outputs,
            "checks": checks, "overall": "PASS" if all(checks.values()) else "BLOCKED"}


def main() -> None:
    """Run preflight and optionally persist its non-scientific diagnostic record."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = inspect(args.config.resolve())
    payload = json.dumps(result, indent=2, allow_nan=False)
    print(payload)
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    if result["overall"] != "PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
