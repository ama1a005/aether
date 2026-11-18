"""Build a provenance-locked SAE matrix from retained Qwen capture tensors."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import numpy as np
import torch


_CAPTURE_NAME = re.compile(
    r"^(?P<case_id>v2_case_\d+)_(?P<role>sender|receiver)_(?P<condition>clean|attacked)\.pt$"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_activation_dataset(
    source_dir: Path,
    output_dir: Path,
    *,
    component_id: str,
    condition: str,
) -> tuple[Path, Path]:
    """Extract one exact component without crossing role or condition boundaries."""
    if condition not in {"clean", "attacked", "both"}:
        raise ValueError("condition must be clean, attacked, or both")
    try:
        role, tensor_key = component_id.split(".", 1)
    except ValueError as error:
        raise ValueError("component_id must start with sender. or receiver.") from error
    if role not in {"sender", "receiver"}:
        raise ValueError("component_id must start with sender. or receiver.")
    if output_dir.exists():
        raise FileExistsError(output_dir)

    rows: list[np.ndarray] = []
    sources: list[dict[str, Any]] = []
    for path in sorted(source_dir.glob("*.pt")):
        match = _CAPTURE_NAME.fullmatch(path.name)
        if match is None or match.group("role") != role:
            continue
        observed_condition = match.group("condition")
        if condition != "both" and observed_condition != condition:
            continue
        payload = torch.load(path, map_location="cpu", weights_only=True)
        if not isinstance(payload, dict) or tensor_key not in payload:
            raise ValueError(f"{path.name} lacks exact component {tensor_key}")
        tensor = payload[tensor_key]
        if not isinstance(tensor, torch.Tensor) or not tensor.is_floating_point():
            raise TypeError(f"{path.name}:{tensor_key} is not a floating tensor")
        if tensor.ndim < 2 or tensor.shape[-1] < 1 or not torch.isfinite(tensor).all():
            raise ValueError(f"{path.name}:{tensor_key} has invalid shape or values")
        matrix = tensor.detach().to(dtype=torch.float32).reshape(-1, tensor.shape[-1]).numpy()
        rows.append(matrix)
        sources.append({
            "case_id": match.group("case_id"),
            "condition": observed_condition,
            "path": path.name,
            "sha256": _sha256(path),
            "source_shape": list(tensor.shape),
            "row_count": int(matrix.shape[0]),
        })
    if not rows:
        raise FileNotFoundError(
            f"no {role} {condition} capture tensors found in {source_dir}"
        )
    dimensions = {row.shape[1] for row in rows}
    if len(dimensions) != 1:
        raise ValueError("capture tensors disagree on hidden dimension")

    matrix = np.concatenate(rows, axis=0).astype(np.float32, copy=False)
    output_dir.mkdir(parents=True)
    data_path = output_dir / f"{component_id.replace('.', '_')}.npy"
    np.save(data_path, matrix, allow_pickle=False)
    manifest = {
        "schema_version": "aether.sae-activation-dataset.v1",
        "component_id": component_id,
        "condition": condition,
        "dtype": str(matrix.dtype),
        "shape": list(matrix.shape),
        "dataset_sha256": _sha256(data_path),
        "source_count": len(sources),
        "sources": sources,
        "split": "development",
        "validation_executions": 0,
        "test_executions": 0,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False), encoding="utf-8"
    )
    return data_path, manifest_path


def main() -> None:
    """CLI for deterministic conversion of retained capture files."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--component-id", required=True)
    parser.add_argument("--condition", choices=("clean", "attacked", "both"), required=True)
    args = parser.parse_args()
    data, manifest = build_activation_dataset(
        args.source_dir, args.output_dir,
        component_id=args.component_id, condition=args.condition,
    )
    print(json.dumps({"data": str(data), "manifest": str(manifest)}, sort_keys=True))


if __name__ == "__main__":
    main()
