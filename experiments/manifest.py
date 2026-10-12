"""Reproducibility manifests for AETHER experiment runs."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

def _require_metadata(name: str, value: str) -> str:
    """Reject blank metadata while permitting explicit unknown states."""
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{name} must be populated or explicitly set to 'unknown'")
    return normalized


def _run(command: Sequence[str], cwd: Path) -> str:
    """Run a metadata command and return stripped stdout, failing explicitly."""
    result = subprocess.run(command, cwd=cwd, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of a file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create_run_manifest(
    *,
    experiment_id: str,
    run_id: str,
    model_id: str,
    model_revision: str,
    tokenizer_revision: str,
    dataset_id: str,
    dataset_version: str,
    dataset_split: str,
    subset_ids: Sequence[str],
    seeds: Sequence[int],
    config_file: Path,
    raw_output_path: Path,
    dataset_files: Sequence[Path] = (),
    prompt_files: Sequence[Path] = (),
    attack_config_files: Sequence[Path] = (),
    intervention_config: dict[str, Any] | None = None,
    search_config: dict[str, Any] | None = None,
    artifact_paths: Sequence[Path] = (),
    timing_seconds: dict[str, float] | None = None,
    repository: Path | None = None,
    command_line: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Build a complete, machine-readable run manifest without hiding failures."""
    repo = (repository or Path.cwd()).resolve()
    if not seeds:
        raise ValueError("at least one random seed is required")
    if not subset_ids:
        raise ValueError("subset_ids must be populated or contain 'not_applicable'")
    metadata = {
        "model_id": _require_metadata("model_id", model_id),
        "model_revision": _require_metadata("model_revision", model_revision),
        "tokenizer_revision": _require_metadata("tokenizer_revision", tokenizer_revision),
        "dataset_id": _require_metadata("dataset_id", dataset_id),
        "dataset_version": _require_metadata("dataset_version", dataset_version),
        "dataset_split": _require_metadata("dataset_split", dataset_split),
    }
    freeze = _run([sys.executable, "-m", "pip", "freeze", "--all"], repo)
    status = _run(["git", "status", "--porcelain"], repo)

    def hashes(paths: Sequence[Path]) -> dict[str, str]:
        return {str(path): sha256_file(repo / path) for path in paths}

    return {
        "manifest_version": "1.0.0",
        "experiment_id": experiment_id,
        "run_id": run_id,
        "utc_timestamp": datetime.now(timezone.utc).isoformat(),
        "git_commit": _run(["git", "rev-parse", "HEAD"], repo),
        "uncommitted_diff": bool(status),
        "dataset_manifest_hashes": hashes(dataset_files),
        **metadata,
        "subset_ids": list(subset_ids),
        "prompt_versions": hashes(prompt_files),
        "random_seeds": list(seeds),
        "hardware": platform.platform(),
        "python_version": platform.python_version(),
        "python_executable": sys.executable,
        "python_env_hash": hashlib.sha256(freeze.encode("utf-8")).hexdigest(),
        "command_line": list(command_line or sys.argv),
        "config_file": str(config_file),
        "config_hash": sha256_file(repo / config_file),
        "attack_configuration_hashes": hashes(attack_config_files),
        "intervention_configuration": intervention_config or {},
        "search_configuration": search_config or {},
        "raw_output_path": str(raw_output_path),
        "artifact_paths": hashes(artifact_paths),
        "timing_seconds": timing_seconds or {},
    }


def write_run_manifest(manifest: dict[str, Any], output_path: Path) -> None:
    """Write a manifest atomically enough for a single local experiment process."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(output_path.suffix + ".tmp")
    temporary.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(output_path)


def main() -> None:
    """Create a manifest for an already executed local experiment artifact."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--model-revision", required=True)
    parser.add_argument("--tokenizer-revision", required=True)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--dataset-version", required=True)
    parser.add_argument("--dataset-split", required=True)
    parser.add_argument("--subset-id", action="append", required=True)
    parser.add_argument("--seed", action="append", type=int, required=True)
    parser.add_argument("--config-file", type=Path, required=True)
    parser.add_argument("--raw-output-path", type=Path, required=True)
    parser.add_argument("--dataset-file", action="append", type=Path, default=[])
    parser.add_argument("--artifact-path", action="append", type=Path, default=[])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = create_run_manifest(
        experiment_id=args.experiment_id,
        run_id=args.run_id,
        model_id=args.model_id,
        model_revision=args.model_revision,
        tokenizer_revision=args.tokenizer_revision,
        dataset_id=args.dataset_id,
        dataset_version=args.dataset_version,
        dataset_split=args.dataset_split,
        subset_ids=args.subset_id,
        seeds=args.seed,
        config_file=args.config_file,
        raw_output_path=args.raw_output_path,
        dataset_files=args.dataset_file,
        artifact_paths=args.artifact_path,
    )
    write_run_manifest(manifest, args.output)


if __name__ == "__main__":
    main()
