"""Verify the transferred snapshot and local-only Transformers loading."""
from __future__ import annotations
import os
from pathlib import Path

from transformers import AutoConfig, AutoTokenizer
from huggingface_hub import snapshot_download

from demo.backend.config import DEFAULT_MODEL_CACHE, MODEL_CACHE_ENV, MODEL_ID, MODEL_PATH_ENV, MODEL_REVISION
from scripts.model_snapshot_manifest import verify

def main() -> None:
    value = os.environ.get(MODEL_PATH_ENV)
    snapshot = Path(value).resolve() if value else Path(snapshot_download(
        repo_id=MODEL_ID,
        revision=MODEL_REVISION,
        cache_dir=Path(os.environ.get(MODEL_CACHE_ENV, DEFAULT_MODEL_CACHE)).resolve(),
        local_files_only=True,
    ))
    payload = verify(snapshot)
    config = AutoConfig.from_pretrained(snapshot, local_files_only=True)
    tokenizer = AutoTokenizer.from_pretrained(snapshot, local_files_only=True)
    print({"revision": payload["resolved_revision"], "model_type": config.model_type,
           "tokenizer": type(tokenizer).__name__, "local_files_only": True})

if __name__ == "__main__":
    main()
