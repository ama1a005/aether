"""Preflight checks for official BFCL evaluation with disclosed Qwen2.5 adapter."""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from importlib.metadata import PackageNotFoundError, version
import json
from pathlib import Path
import sys
from typing import Any, Sequence

import torch

PINNED_PACKAGE = "bfcl_eval"
PINNED_PACKAGE_VERSION = "2026.3.23"
PINNED_WHEEL_SHA256 = "3bb6dfa5f0c68ad403c9ec50b00db2bb3b4cc9b38ab1ff33f48fe30d853d3a0a"
PINNED_MODEL_ID = "Qwen/Qwen2.5-1.5B-Instruct"
PINNED_MODEL_REVISION = "989aa7980e4cf806f80c7fef2b1adb7bc71aa306"
ADAPTER_REGISTRY_NAME = "AETHER/Qwen2.5-1.5B-Instruct-FC"
VALID_OFFICIAL_CATEGORIES = frozenset({
    "simple", "multiple", "parallel", "parallel_multiple",
    "irrelevance", "live_simple", "live_multiple", "live_parallel",
    "live_parallel_multiple", "live_relevance", "rest", "sql", "java", "javascript"
})
PHASE1_CATEGORIES = ("simple", "multiple", "parallel", "irrelevance")


@dataclass(frozen=True)
class BFCLPreflightResult:
    """Preflight outcome for BFCL run."""
    passed: bool
    reasons: tuple[str, ...]
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "reasons": list(self.reasons),
            "details": self.details,
        }


def check_package(
    package_name: str = PINNED_PACKAGE,
    expected_version: str = PINNED_PACKAGE_VERSION,
    wheel_path: Path | None = None,
    expected_wheel_sha256: str = PINNED_WHEEL_SHA256,
) -> tuple[bool, list[str], dict[str, Any]]:
    """Verify package installation, version and optional wheel hash."""
    reasons = []
    details: dict[str, Any] = {"package": package_name, "expected_version": expected_version}
    try:
        installed = version(package_name)
        details["installed_version"] = installed
        if installed != expected_version:
            reasons.append(
                f"{package_name} version mismatch: expected {expected_version}, found {installed}"
            )
    except PackageNotFoundError:
        details["installed_version"] = None
        reasons.append(f"Required package {package_name} is not installed")

    if wheel_path is not None:
        if not wheel_path.is_file():
            reasons.append(f"Declared wheel file does not exist: {wheel_path}")
        else:
            digest = sha256(wheel_path.read_bytes()).hexdigest()
            details["wheel_sha256"] = digest
            if digest != expected_wheel_sha256:
                reasons.append(
                    f"Wheel hash mismatch: expected {expected_wheel_sha256}, got {digest}"
                )
    return len(reasons) == 0, reasons, details


def check_backend_and_hardware(
    backend: str = "vllm",
    num_gpus: int = 1,
    min_vram_gb: float = 6.0,
) -> tuple[bool, list[str], dict[str, Any]]:
    """Verify inference backend requirements and GPU resources."""
    reasons = []
    details: dict[str, Any] = {
        "backend": backend,
        "num_gpus_requested": num_gpus,
        "cuda_available": torch.cuda.is_available(),
    }
    if backend not in {"vllm", "sglang"}:
        reasons.append(f"Unsupported backend {backend!r}; only 'vllm' and 'sglang' supported")

    if not torch.cuda.is_available():
        reasons.append(
            f"Backend {backend} requires CUDA GPU, but CUDA is not available on this system"
        )
        details["gpu_count"] = 0
    else:
        count = torch.cuda.device_count()
        details["gpu_count"] = count
        if count < num_gpus:
            reasons.append(f"Requested {num_gpus} GPUs, but only {count} available")
        else:
            for idx in range(num_gpus):
                props = torch.cuda.get_device_properties(idx)
                total_vram_gb = props.total_memory / (1024 ** 3)
                details[f"gpu_{idx}_name"] = props.name
                details[f"gpu_{idx}_vram_gb"] = round(total_vram_gb, 2)
                if total_vram_gb < min_vram_gb:
                    reasons.append(
                        f"GPU {idx} ({props.name}) has {total_vram_gb:.1f} GB VRAM, "
                        f"below required {min_vram_gb} GB"
                    )
    return len(reasons) == 0, reasons, details


def check_snapshot_manifest(
    manifest_path: Path,
    expected_revision: str = PINNED_MODEL_REVISION,
    expected_model_id: str = PINNED_MODEL_ID,
    verify_file_hashes: bool = True,
) -> tuple[bool, list[str], dict[str, Any]]:
    """Validate snapshot manifest and its constituent files."""
    reasons = []
    details: dict[str, Any] = {"manifest_path": str(manifest_path)}
    if not manifest_path.is_file():
        reasons.append(f"Model snapshot manifest not found: {manifest_path}")
        return False, reasons, details

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        reasons.append(f"Failed to parse snapshot manifest JSON: {exc}")
        return False, reasons, details

    model_id = manifest.get("model_id")
    details["model_id"] = model_id
    if model_id != expected_model_id:
        reasons.append(f"Model ID mismatch: expected {expected_model_id}, found {model_id}")

    revision = manifest.get("resolved_revision")
    details["resolved_revision"] = revision
    if revision != expected_revision:
        reasons.append(
            f"Revision mismatch: expected {expected_revision}, found {revision}"
        )

    snapshot_dir = Path(manifest.get("snapshot_path", ""))
    details["snapshot_path"] = str(snapshot_dir)
    if not snapshot_dir.is_dir():
        reasons.append(f"Snapshot directory does not exist: {snapshot_dir}")
        return False, reasons, details

    files = manifest.get("files", [])
    if not files or not isinstance(files, list):
        reasons.append("Snapshot manifest contains no files entry")
        return False, reasons, details

    details["file_count"] = len(files)
    if verify_file_hashes:
        for item in files:
            rel = Path(item["path"])
            if rel.is_absolute() or ".." in rel.parts:
                reasons.append(f"Unsafe path in manifest: {rel}")
                continue
            target = snapshot_dir / rel
            if not target.is_file():
                reasons.append(f"Missing snapshot file: {rel}")
                continue
            if target.stat().st_size != item["size"]:
                reasons.append(
                    f"File size mismatch for {rel}: expected {item['size']}, "
                    f"found {target.stat().st_size}"
                )
                continue
            digest = sha256(target.read_bytes()).hexdigest()
            if digest != item["sha256"]:
                reasons.append(
                    f"SHA256 mismatch for {rel}: expected {item['sha256']}, found {digest}"
                )
    return len(reasons) == 0, reasons, details


def check_categories(
    categories: Sequence[str] = PHASE1_CATEGORIES,
) -> tuple[bool, list[str], dict[str, Any]]:
    """Validate requested categories against official BFCL definitions."""
    reasons = []
    details = {"categories": list(categories)}
    if not categories:
        reasons.append("Category list cannot be empty")
        return False, reasons, details
    unknown = [cat for cat in categories if cat not in VALID_OFFICIAL_CATEGORIES]
    if unknown:
        reasons.append(f"Unknown BFCL categories: {unknown}")
    return len(reasons) == 0, reasons, details


def run_bfcl_preflight(
    manifest_path: Path,
    categories: Sequence[str] = PHASE1_CATEGORIES,
    backend: str = "vllm",
    num_gpus: int = 1,
    wheel_path: Path | None = None,
    verify_snapshot_hashes: bool = True,
) -> BFCLPreflightResult:
    """Run all BFCL preflight checks and return consolidated result."""
    all_reasons = []
    all_details: dict[str, Any] = {}

    pkg_ok, pkg_reasons, pkg_details = check_package(wheel_path=wheel_path)
    all_reasons.extend(pkg_reasons)
    all_details["package"] = pkg_details

    hw_ok, hw_reasons, hw_details = check_backend_and_hardware(
        backend=backend, num_gpus=num_gpus
    )
    all_reasons.extend(hw_reasons)
    all_details["hardware"] = hw_details

    snap_ok, snap_reasons, snap_details = check_snapshot_manifest(
        manifest_path=manifest_path,
        verify_file_hashes=verify_snapshot_hashes,
    )
    all_reasons.extend(snap_reasons)
    all_details["snapshot"] = snap_details

    cat_ok, cat_reasons, cat_details = check_categories(categories)
    all_reasons.extend(cat_reasons)
    all_details["categories"] = cat_details

    passed = pkg_ok and hw_ok and snap_ok and cat_ok
    return BFCLPreflightResult(passed=passed, reasons=tuple(all_reasons), details=all_details)
