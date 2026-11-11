"""Disclosed BFCL adapter for the frozen AETHER Qwen2.5 primary model.

BFCL 2026.3.23 ships a Qwen function-calling handler but does not register
Qwen2.5. This module adds only that registry entry, then delegates generation
and evaluation to BFCL's public CLI. It is not an unmodified BFCL leaderboard
model configuration.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Any, MutableMapping, Sequence


REGISTRY_NAME = "AETHER/Qwen2.5-1.5B-Instruct-FC"
MODEL_ID = "Qwen/Qwen2.5-1.5B-Instruct"


def register_qwen25(
    mapping: MutableMapping[str, Any], model_config_type: type[Any], handler: type[Any]
) -> None:
    """Register the disclosed primary-model adapter without replacing entries."""
    if REGISTRY_NAME in mapping:
        existing = mapping[REGISTRY_NAME]
        if getattr(existing, "model_name", None) != MODEL_ID:
            raise RuntimeError(f"BFCL registry collision for {REGISTRY_NAME}")
        return
    mapping[REGISTRY_NAME] = model_config_type(
        model_name=MODEL_ID,
        display_name="AETHER Qwen2.5-1.5B-Instruct (FC adapter)",
        url=f"https://huggingface.co/{MODEL_ID}",
        org="Qwen",
        license="apache-2.0",
        model_handler=handler,
        input_price=None,
        output_price=None,
        is_fc_model=True,
        underscore_to_dot=False,
    )


def verify_snapshot_manifest(path: Path, expected_revision: str) -> Path:
    """Verify the pinned model snapshot manifest and every declared file hash."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("model_id") != MODEL_ID:
        raise ValueError(f"snapshot model mismatch: {payload.get('model_id')!r}")
    if payload.get("resolved_revision") != expected_revision:
        raise ValueError("snapshot revision mismatch")
    snapshot = Path(payload.get("snapshot_path", "")).resolve()
    if not snapshot.is_dir() or snapshot.name != expected_revision:
        raise ValueError("snapshot path is absent or not the pinned revision directory")
    files = payload.get("files")
    if not isinstance(files, list) or not files:
        raise ValueError("snapshot manifest has no files")
    for entry in files:
        relative = Path(entry["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"unsafe snapshot path: {relative}")
        target = snapshot / relative
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        if target.stat().st_size != entry["size"] or digest != entry["sha256"]:
            raise ValueError(f"snapshot artifact mismatch: {relative.as_posix()}")
    return snapshot


def _consume_adapter_arguments(arguments: Sequence[str]) -> tuple[list[str], str, Path]:
    """Remove required adapter provenance flags before BFCL parses its CLI."""
    remaining = list(arguments)
    values: dict[str, str] = {}
    for flag in ("--model-revision", "--snapshot-manifest"):
        if flag not in remaining:
            raise ValueError(f"required adapter argument missing: {flag}")
        index = remaining.index(flag)
        if index + 1 >= len(remaining):
            raise ValueError(f"adapter argument has no value: {flag}")
        values[flag] = remaining[index + 1]
        del remaining[index:index + 2]
    return remaining, values["--model-revision"], Path(values["--snapshot-manifest"])


def main(arguments: Sequence[str] | None = None) -> None:
    """Validate provenance, register Qwen2.5, and run the official BFCL CLI."""
    raw = list(sys.argv[1:] if arguments is None else arguments)
    remaining, revision, manifest = _consume_adapter_arguments(raw)
    snapshot = verify_snapshot_manifest(manifest, revision)
    if "generate" in remaining:
        if "--local-model-path" in remaining:
            raise ValueError("local model path is controlled by the verified snapshot manifest")
        remaining.extend(("--local-model-path", str(snapshot)))

    from bfcl_eval.constants.model_config import MODEL_CONFIG_MAPPING, ModelConfig
    from bfcl_eval.model_handler.local_inference.qwen_fc import QwenFCHandler

    register_qwen25(MODEL_CONFIG_MAPPING, ModelConfig, QwenFCHandler)
    from bfcl_eval.__main__ import cli

    sys.argv = [sys.argv[0], *remaining]
    cli()


if __name__ == "__main__":
    main()
