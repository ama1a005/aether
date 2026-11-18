"""Fail-closed validation for the prospective Qwen SAE training protocol."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


QUALIFIED_MODEL = "Qwen/Qwen2.5-1.5B-Instruct"
QUALIFIED_REVISION = "989aa7980e4cf806f80c7fef2b1adb7bc71aa306"
ALLOWED_COMPONENT = "receiver.module.L22.attention_output"
AMENDMENT_SCHEMA = "aether.qwen-sae-training-freeze-amendment.v1.1"


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


def load_and_validate_amendment(
    path: Path, base_path: Path, *, require_approval: bool = False
) -> dict[str, Any]:
    """Validate the corpus-source correction without weakening the v1 gates."""
    amendment = json.loads(path.read_text(encoding="utf-8"))
    if amendment.get("schema_version") != AMENDMENT_SCHEMA:
        raise ValueError("unexpected SAE amendment schema")
    if amendment.get("base_protocol_sha256") != sha256_file(base_path):
        raise ValueError("SAE amendment base-protocol hash mismatch")
    base = load_and_validate_freeze(base_path)
    corpus = amendment.get("training_corpus", {})
    required_corpus = {
        "dataset_id": "Salesforce/wikitext",
        "dataset_revision": "de54f133ef530c2e9b46c532f95a01c446ff0f1d",
        "dataset_config": "wikitext-2-raw-v1",
        "source_split": "train",
        "selected_token_count": 65536,
        "training_token_count": 57344,
        "checkpoint_selection_token_count": 8192,
        "sequence_length": 256,
    }
    wrong = [key for key, value in required_corpus.items() if corpus.get(key) != value]
    if wrong:
        raise ValueError(f"SAE amendment corpus mismatch: {wrong}")
    if corpus["training_token_count"] < base["minimum_training_rows"]:
        raise ValueError("SAE amendment weakens the minimum training-row gate")
    if (corpus["training_token_count"] + corpus["checkpoint_selection_token_count"]
            != corpus["selected_token_count"]):
        raise ValueError("SAE amendment token partitions do not exhaust the selection")
    if corpus["selected_token_count"] % corpus["sequence_length"]:
        raise ValueError("SAE amendment permits an ambiguous remainder")
    if corpus.get("protected_aether_cases_used_for_training") != []:
        raise PermissionError("SAE amendment trains on protected AETHER cases")
    audit = amendment.get("aether_final_audit", {})
    if audit.get("case_ids") != base["audit_case_ids"]:
        raise ValueError("SAE amendment changes the frozen AETHER audit cases")
    if amendment.get("validation_executions") != 0 or amendment.get("test_executions") != 0:
        raise PermissionError("SAE amendment opens a protected split")
    if amendment.get("status") != "awaiting_human_scientific_review":
        raise ValueError("unexpected SAE amendment status")
    review = amendment.get("human_review", {})
    if require_approval and not (
        review.get("approved") is True and review.get("reviewer") and review.get("utc_timestamp")
    ):
        raise PermissionError("SAE training amendment lacks exact human approval")
    return amendment


def verify_human_decision(protocol_path: Path, decision_path: Path) -> dict[str, Any]:
    """Verify a separate human decision against the immutable proposal bytes."""
    load_and_validate_freeze(protocol_path)
    decision = json.loads(decision_path.read_text(encoding="utf-8"))
    if decision.get("decision") != "APPROVED":
        raise PermissionError("SAE training freeze is not approved")
    if decision.get("proposal_sha256") != sha256_file(protocol_path):
        raise PermissionError("SAE training decision does not match the proposal hash")
    if decision.get("reviewer_role") != "human_project_owner":
        raise PermissionError("SAE training decision lacks a human project owner")
    return decision
