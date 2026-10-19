"""Explicitly download the pinned demo model; never called during server startup."""

from __future__ import annotations

import os
from pathlib import Path

from huggingface_hub import snapshot_download

from demo.backend.config import DEFAULT_MODEL_CACHE, MODEL_CACHE_ENV, MODEL_ID, MODEL_REVISION
from scripts.model_snapshot_manifest import create


def main() -> None:
    """Download one immutable Hugging Face revision into the configured external cache."""
    cache_dir = Path(os.environ.get(MODEL_CACHE_ENV, DEFAULT_MODEL_CACHE)).resolve()
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = snapshot_download(repo_id=MODEL_ID, revision=MODEL_REVISION, cache_dir=cache_dir)
    create(Path(path))
    print(f"Downloaded {MODEL_ID}@{MODEL_REVISION} to {path}")


if __name__ == "__main__":
    main()
