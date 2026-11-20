"""Fail-closed validation for prospective second-model qualification."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any


SCHEMA = "aether.second-model-qualification-freeze.v1"
PRIMARY = "Qwen/Qwen2.5-1.5B-Instruct"
DISQUALIFIED = {"Qwen/Qwen2.5-0.5B-Instruct"}


def sha256_file(path: Path) -> str:
    """Return a file's SHA-256."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_and_validate(path: Path, repository: Path) -> dict[str, Any]:
    """Validate immutable identity, unchanged tasks, resources and split locks."""
    proposal = json.loads(path.read_text(encoding="utf-8"))
    if proposal.get("schema_version") != SCHEMA:
        raise ValueError("unsupported second-model freeze schema")
    if proposal.get("status") != "awaiting_human_scientific_review":
        raise ValueError("unexpected second-model freeze status")
    model = proposal.get("model", {})
    if model.get("model_id") == PRIMARY or model.get("model_id") in DISQUALIFIED:
        raise ValueError("second-model candidate is primary or previously disqualified")
    if re.fullmatch(r"[0-9a-f]{40}", str(model.get("revision", ""))) is None:
        raise ValueError("second-model revision is not an immutable 40-hex commit")
    if model.get("tokenizer_revision") != model.get("revision"):
        raise ValueError("second-model tokenizer revision differs from model revision")
    if model.get("trust_remote_code") is not False:
        raise PermissionError("second-model proposal permits remote model code")
    execution = proposal.get("execution", {})
    required_execution = {
        "device": "cpu", "dtype": "float32", "quantized": False,
        "explicit_offload": False, "disk_offload": False,
        "low_cpu_mem_usage": True, "local_files_only_after_snapshot": True,
    }
    wrong = [key for key, value in required_execution.items() if execution.get(key) != value]
    if wrong:
        raise ValueError(f"second-model execution mismatch: {wrong}")
    behavioral = proposal.get("behavioral_qualification", {})
    for path_key, hash_key in (("cases_path", "cases_sha256"),
                               ("controls_path", "controls_sha256")):
        source = repository / str(behavioral.get(path_key, ""))
        if not source.is_file() or sha256_file(source) != behavioral.get(hash_key):
            raise ValueError(f"second-model frozen input mismatch: {path_key}")
    instrumentation = proposal.get("instrumentation_acceptance", {})
    layer_count = model.get("expected_layer_count")
    layers = instrumentation.get("capture_layers")
    if not isinstance(layer_count, int) or not isinstance(layers, list) or layers != [0, layer_count // 2, layer_count - 1]:
        raise ValueError("second-model instrumentation layers are not architecture-relative")
    if instrumentation.get("head_capture_layer") != layer_count // 2:
        raise ValueError("second-model head-capture layer mismatch")
    if proposal.get("validation_executions") != 0 or proposal.get("test_executions") != 0:
        raise PermissionError("second-model proposal opens a protected split")
    return proposal


def verify_decision(proposal_path: Path, decision_path: Path) -> dict[str, Any]:
    """Require a separate human decision matching the immutable proposal bytes."""
    decision = json.loads(decision_path.read_text(encoding="utf-8"))
    if decision.get("decision") != "APPROVED":
        raise PermissionError("second-model freeze is not approved")
    if decision.get("proposal_sha256") != sha256_file(proposal_path):
        raise PermissionError("second-model decision hash mismatch")
    if decision.get("reviewer_role") != "human_project_owner":
        raise PermissionError("second-model decision lacks a human project owner")
    expected = (
        "I approve SmolLM2 second-model qualification freeze v1 SHA-256 "
        f"{sha256_file(proposal_path)}"
    )
    if decision.get("approval_text") != expected:
        raise PermissionError("second-model decision does not contain the exact approval text")
    return decision
