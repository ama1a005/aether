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
AMENDMENT_V1_2_SCHEMA = "aether.qwen-sae-training-freeze-amendment.v1.2"
AMENDMENT_V1_3_SCHEMA = "aether.qwen-sae-training-freeze-amendment.v1.3"


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


def load_and_validate_v1_2_amendment(
    path: Path, v1_1_path: Path, base_path: Path, *, require_approval: bool = False
) -> dict[str, Any]:
    """Validate the retrieval-only v1.2 correction against approved v1.1."""
    amendment = json.loads(path.read_text(encoding="utf-8"))
    if amendment.get("schema_version") != AMENDMENT_V1_2_SCHEMA:
        raise ValueError("unexpected SAE v1.2 amendment schema")
    if amendment.get("parent_amendment_sha256") != sha256_file(v1_1_path):
        raise ValueError("SAE v1.2 parent-amendment hash mismatch")
    load_and_validate_amendment(v1_1_path, base_path)
    expected = {
        "dataset_id": "Salesforce/wikitext",
        "dataset_revision": "b08601e04326c79dfdd32d625aee71d232d685c3",
        "dataset_config": "wikitext-2-raw-v1",
        "source_split": "train",
        "source_file": "wikitext-2-raw-v1/train-00000-of-00001.parquet",
        "source_file_sha256": "e83889baabc497075506f91975be5fac0d45c5290b6b20582c8cd1e853d0c9f7",
    }
    correction = amendment.get("correction", {})
    wrong = [key for key, value in expected.items() if correction.get(key) != value]
    if wrong:
        raise ValueError(f"SAE v1.2 corpus retrieval mismatch: {wrong}")
    if amendment.get("validation_executions") != 0 or amendment.get("test_executions") != 0:
        raise PermissionError("SAE v1.2 opens a protected split")
    if amendment.get("status") != "awaiting_human_scientific_review":
        raise ValueError("unexpected SAE v1.2 status")
    review = amendment.get("human_review", {})
    if require_approval and not (
        review.get("approved") is True and review.get("reviewer") and review.get("utc_timestamp")
    ):
        raise PermissionError("SAE v1.2 lacks exact human approval")
    return amendment


def load_and_validate_v1_3_amendment(
    path: Path, v1_2_path: Path, v1_1_path: Path, base_path: Path,
    *, require_approval: bool = False,
) -> dict[str, Any]:
    """Validate the execution-only v1.3 correction without weakening gates."""
    amendment = json.loads(path.read_text(encoding="utf-8"))
    if amendment.get("schema_version") != AMENDMENT_V1_3_SCHEMA:
        raise ValueError("unexpected SAE v1.3 amendment schema")
    if amendment.get("parent_amendment_sha256") != sha256_file(v1_2_path):
        raise ValueError("SAE v1.3 parent-amendment hash mismatch")
    load_and_validate_v1_2_amendment(v1_2_path, v1_1_path, base_path)
    base = load_and_validate_freeze(base_path)
    execution = amendment.get("execution_semantics", {})
    if execution.get("preeligibility_early_stopping") != "forbidden":
        raise ValueError("SAE v1.3 must forbid pre-eligibility early stopping")
    if execution.get("maximum_epochs_unchanged") != base["optimization"]["maximum_epochs"]:
        raise ValueError("SAE v1.3 changes maximum epochs")
    if execution.get("posteligibility_patience") != base["optimization"]["early_stopping_patience"]:
        raise ValueError("SAE v1.3 changes patience")
    unchanged = set(amendment.get("unchanged", []))
    required = {"optimizer_learning_rate_batch_size_l1_coefficient_and_loss",
                "minimum_active_fraction_0_001", "maximum_active_fraction_0_2",
                "maximum_relative_reconstruction_error_0_1", "validation_and_test_locks"}
    if not required.issubset(unchanged):
        raise ValueError("SAE v1.3 omits a frozen scientific gate")
    if amendment.get("validation_executions") != 0 or amendment.get("test_executions") != 0:
        raise PermissionError("SAE v1.3 opens a protected split")
    if amendment.get("status") != "awaiting_human_scientific_review":
        raise ValueError("unexpected SAE v1.3 status")
    review = amendment.get("human_review", {})
    if require_approval and not (
        review.get("approved") is True and review.get("reviewer") and review.get("utc_timestamp")
    ):
        raise PermissionError("SAE v1.3 lacks exact human approval")
    return amendment
