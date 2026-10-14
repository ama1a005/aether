"""Deterministic locked paired-task split construction."""

from __future__ import annotations

from hashlib import sha256
import json


def frozen_splits(pair_ids: list[str]) -> dict[str, list[str]]:
    """Create fixed 16/4/4 development/validation/test splits from 24 IDs."""
    if len(pair_ids) != 24 or len(set(pair_ids)) != 24:
        raise ValueError("the frozen split requires exactly 24 unique pair IDs")
    ordered = sorted(pair_ids)
    return {"development": ordered[:16], "validation": ordered[16:20], "test": ordered[20:]}


def split_hash(splits: dict[str, list[str]]) -> str:
    """Hash canonical split membership."""
    payload = json.dumps(splits, sort_keys=True, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()


def require_development(pair_id: str, splits: dict[str, list[str]]) -> None:
    """Prevent validation/test causal execution during this stage."""
    if pair_id not in splits["development"]:
        raise PermissionError(f"pair {pair_id} is locked outside development")
