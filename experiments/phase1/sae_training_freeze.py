"""Fail-closed validation for the prospective Qwen SAE training protocol."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


QUALIFIED_MODEL = "Qwen/Qwen2.5-1.5B-Instruct"
QUALIFIED_REVISION = "989aa7980e4cf806f80c7fef2b1adb7bc71aa306"
ALLOWED_COMPONENT = "receiver.module.L22.attention_output"


def sha256_file(path: Path) -> str:
    """Return the SHA-256 of a protocol file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_and_validate_freeze(path: Path, *, require_approval: bool = False) -> dict[str, Any]:
    """Validate identities, split isolation, metrics, and human-review state."""
    protocol = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "schema_version": "aether.qwen-sae-training-freeze.v1",
        "split": "development",
        "model_id": QUALIFIED_MODEL,
        "model_revision": QUALIFIED_REVISION,
        "component_id": ALLOWED_COMPONENT,
        "hidden_width": 1536,
        "validation_executions": 0,
        "test_executions": 0,
    }
    wrong = [key for key, value in expected.items() if protocol.get(key) != value]
    if wrong:
        raise ValueError(f"SAE freeze identity mismatch: {wrong}")
    archive_hash = protocol.get("activation_archive_sha256")
    if not isinstance(archive_hash, str) or len(archive_hash) != 64:
        raise ValueError("SAE freeze requires an activation archive SHA-256")
    train = protocol.get("train_case_ids")
    audit = protocol.get("audit_case_ids")
    excluded = protocol.get("excluded_case_ids")
    if not all(isinstance(group, list) and group for group in (train, audit, excluded)):
        raise ValueError("SAE freeze requires nonempty train, audit, and excluded case lists")
    if any(len(group) != len(set(group)) for group in (train, audit, excluded)):
        raise ValueError("SAE freeze case lists contain duplicates")
    if set(train) & set(audit) or set(train) & set(excluded) or set(audit) & set(excluded):
        raise ValueError("SAE freeze case partitions overlap")
    if protocol.get("minimum_training_rows", 0) < protocol["hidden_width"]:
        raise ValueError("SAE freeze permits an underdetermined training matrix")
    architecture = protocol.get("architecture", {})
    if architecture.get("input_dim") != protocol["hidden_width"]:
        raise ValueError("SAE architecture input dimension mismatch")
    acceptance = protocol.get("acceptance", {})
    threshold = acceptance.get("maximum_relative_reconstruction_error")
    if not isinstance(threshold, (int, float)) or not 0 < threshold < 1:
        raise ValueError("SAE reconstruction threshold must be in (0, 1)")
    if protocol.get("status") != "awaiting_human_scientific_review":
        raise ValueError("unexpected SAE freeze status")
    review = protocol.get("human_review", {})
    if require_approval and not (
        review.get("approved") is True and review.get("reviewer") and review.get("utc_timestamp")
    ):
        raise PermissionError("SAE training freeze lacks exact human approval")
    return protocol
