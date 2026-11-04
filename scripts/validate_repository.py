"""Validate checked-in configuration and guard against official-evidence leakage."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess

import yaml

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_SUFFIXES = {".pt", ".npy", ".npz", ".safetensors", ".bin"}


def validate() -> None:
    """Fail for malformed configs, tracked tensors, or unmanifested official results."""
    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, check=True,
                             capture_output=True, text=True).stdout.splitlines()
    bad = [path for path in tracked if Path(path).suffix.lower() in FORBIDDEN_SUFFIXES]
    if bad:
        raise ValueError(f"Tracked binary/model artifacts are forbidden: {bad}")
    for path in [*ROOT.glob("configs/**/*.json"), *ROOT.glob("configs/**/*.yaml")]:
        with path.open(encoding="utf-8") as handle:
            payload = json.load(handle) if path.suffix == ".json" else yaml.safe_load(handle)
        if payload is None:
            raise ValueError(f"Empty configuration: {path}")
    official = ROOT / "results/official"
    if official.exists():
        for child in official.iterdir():
            if child.is_dir() and not (child / "manifest.json").is_file():
                raise ValueError(f"Official result directory lacks manifest: {child}")


if __name__ == "__main__":
    validate()
