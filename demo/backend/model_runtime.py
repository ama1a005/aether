"""Explicit, singleton, local-only model warm-up for the review UI."""

from __future__ import annotations

import os
from pathlib import Path
from threading import Lock
from typing import Any

import psutil
import torch

from instrumentation.adapters.qwen2 import Qwen2ModelAdapter
from demo.backend.service import MODEL_ID, MODEL_REVISION

_lock = Lock()
_adapter: Qwen2ModelAdapter | None = None
_error: str | None = None


def model_status() -> dict[str, Any]:
    """Report honest process/system memory and singleton load state."""
    memory = psutil.virtual_memory()
    process = psutil.Process().memory_info()
    return {
        "model_id": MODEL_ID, "model_revision": MODEL_REVISION,
        "ready": _adapter is not None, "last_error": _error,
        "device": "cuda" if torch.cuda.is_available() else "cpu",
        "system_available_gib": round(memory.available / 2**30, 2),
        "process_rss_gib": round(process.rss / 2**30, 2),
        "policy": "single instance; local cache only; no download",
    }


def preload_model() -> dict[str, Any]:
    """Load the pinned review model once, failing explicitly if unavailable."""
    global _adapter, _error
    with _lock:
        if _adapter is not None:
            return model_status()
        cache_dir = Path(os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface"))
        device = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = torch.float16 if device == "cuda" else torch.float32
        candidate = Qwen2ModelAdapter(MODEL_ID, MODEL_REVISION, cache_dir, dtype=dtype, device=device, local_files_only=True)
        try:
            candidate.load()
        except (OSError, RuntimeError, ValueError) as exc:
            _error = f"{type(exc).__name__}: {exc}"
            raise RuntimeError(_error) from exc
        _adapter = candidate
        _error = None
        return model_status()
