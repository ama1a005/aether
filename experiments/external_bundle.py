"""Hash, verify and atomically promote externally executed experiment bundles."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
import platform
from typing import Any, Mapping


@dataclass(frozen=True)
class VerifiedBundle:
    """Identity returned only after every declared artifact verifies."""

    experiment_id: str
    run_id: str
    evidence_kind: str
    artifact_count: int


def runtime_metadata(*, repository: Path, experiment_id: str, run_id: str,
                     dataset_manifest_hashes: Mapping[str, str], model_id: str,
                     model_revision: str, tokenizer_revision: str, seeds: list[int],
                     config_file: Path, evidence_kind: str) -> dict[str, Any]:
    """Collect mandatory runtime provenance and reject a dirty source tree."""
    def command(values: list[str]) -> str:
        return subprocess.run(values, cwd=repository, check=True, capture_output=True, text=True).stdout.strip()
    status = command(["git", "status", "--porcelain"])
    freeze = command([sys.executable, "-m", "pip", "freeze", "--all"])
    return {
        "experiment_id": experiment_id, "run_id": run_id,
        "utc_timestamp": datetime.now(timezone.utc).isoformat(),
        "git_commit": command(["git", "rev-parse", "HEAD"]), "uncommitted_diff": bool(status),
        "dataset_manifest_hashes": dict(dataset_manifest_hashes), "model_id": model_id,
        "model_revision": model_revision, "tokenizer_revision": tokenizer_revision,
        "random_seeds": seeds, "hardware": platform.platform(),
        "python_env_hash": hashlib.sha256(freeze.encode()).hexdigest(),
        "command_line": sys.argv, "config_file": str(config_file), "evidence_kind": evidence_kind,
        "validation_executions": 0, "test_executions": 0,
    }


def sha256_file(path: Path) -> str:
    """Return the streaming SHA-256 digest of one file."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def artifact_hashes(root: Path, *, exclude: tuple[str, ...] = ("bundle_manifest.json",)) -> dict[str, str]:
    """Hash every regular bundle file using safe POSIX-relative names."""
    if not root.is_dir():
        raise FileNotFoundError(root)
    hashes: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"bundle contains a symlink: {path}")
        if path.is_file():
            relative = path.relative_to(root).as_posix()
            if relative not in exclude:
                hashes[relative] = sha256_file(path)
    if not hashes:
        raise ValueError("external bundle contains no artifacts")
    return hashes


def write_bundle_manifest(root: Path, metadata: Mapping[str, Any]) -> Path:
    """Write a manifest after validating required reproducibility metadata."""
    required = {
        "experiment_id", "run_id", "utc_timestamp", "git_commit",
        "uncommitted_diff", "dataset_manifest_hashes", "model_id",
        "model_revision", "tokenizer_revision", "random_seeds", "hardware",
        "python_env_hash", "command_line", "config_file", "evidence_kind",
        "validation_executions", "test_executions",
    }
    missing = sorted(required - metadata.keys())
    if missing:
        raise ValueError(f"external bundle metadata is incomplete: {missing}")
    if metadata["uncommitted_diff"] is not False:
        raise ValueError("evidence bundle requires a clean source tree")
    payload = {"schema_version": "aether.external-bundle.v1", **dict(metadata)}
    payload["artifacts"] = artifact_hashes(root)
    destination = root / "bundle_manifest.json"
    destination.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False), encoding="utf-8")
    return destination


def verify_bundle(root: Path, *, expected_kind: str | None = None) -> VerifiedBundle:
    """Verify manifest identity, split locks and the exact artifact inventory."""
    manifest_path = root / "bundle_manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"bundle manifest missing: {manifest_path}")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "aether.external-bundle.v1":
        raise ValueError("unsupported external bundle schema")
    if payload.get("uncommitted_diff") is not False:
        raise ValueError("dirty-source bundle is not admissible")
    if payload.get("validation_executions") != 0 or payload.get("test_executions") != 0:
        raise ValueError("external development bundle accessed a protected split")
    if expected_kind is not None and payload.get("evidence_kind") != expected_kind:
        raise ValueError("external bundle evidence kind mismatch")
    declared = payload.get("artifacts")
    if not isinstance(declared, dict) or not declared:
        raise ValueError("external bundle has no declared artifacts")
    observed = artifact_hashes(root)
    if observed != declared:
        raise ValueError("external bundle inventory or artifact hash mismatch")
    for key in ("experiment_id", "run_id", "model_id", "model_revision", "tokenizer_revision"):
        if not isinstance(payload.get(key), str) or not payload[key]:
            raise ValueError(f"external bundle lacks {key}")
    return VerifiedBundle(payload["experiment_id"], payload["run_id"], payload["evidence_kind"], len(observed))


def ingest_bundle(source: Path, destination: Path, *, expected_kind: str | None = None) -> VerifiedBundle:
    """Verify, copy through staging, reverify and refuse destination overwrite."""
    verified = verify_bundle(source, expected_kind=expected_kind)
    if destination.exists():
        raise FileExistsError(f"evidence destination already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f".{destination.name}-", dir=destination.parent) as temporary:
        staged = Path(temporary) / destination.name
        shutil.copytree(source, staged)
        verify_bundle(staged, expected_kind=expected_kind)
        staged.replace(destination)
    return verified
