"""AttackDelta validation and corpus hashing for M2 provenance.

Validates that attack deltas change only permitted fields and provides
corpus-level SHA-256 fingerprinting for reproducibility manifests.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, List, Tuple


@dataclass(frozen=True)
class AttackDelta:
    """Structured record of authorized changes between clean and attacked trajectories."""

    attack_id: str
    case_id: str
    clean_fields: dict[str, Any]
    attacked_fields: dict[str, Any]
    permitted_changes: tuple[str, ...]
    actual_changes: tuple[str, ...]
    timestamp: str
    corpus_hash: str


def validate_delta(delta: AttackDelta) -> Tuple[bool, List[str]]:
    """Validate that an AttackDelta conforms to the declared threat model.

    Returns:
        (True, []) if valid; (False, [error_messages]) otherwise.
    """
    errors: list[str] = []

    if not delta.attack_id or not delta.attack_id.strip():
        errors.append("attack_id must not be blank")

    if not delta.case_id or not delta.case_id.strip():
        errors.append("case_id must not be blank")

    if not delta.corpus_hash or not delta.corpus_hash.strip():
        errors.append("corpus_hash must not be blank")

    if not delta.actual_changes:
        errors.append("actual_changes is empty; no-op delta is invalid")

    unauthorized = set(delta.actual_changes) - set(delta.permitted_changes)
    if unauthorized:
        errors.append(
            f"over-broad delta: unauthorized field changes {sorted(unauthorized)}"
        )

    return (len(errors) == 0, errors)


def compute_delta(
    clean_msg: dict[str, Any],
    attacked_msg: dict[str, Any],
    permitted_fields: list[str],
    attack_id: str,
    case_id: str,
    corpus_hash: str,
) -> AttackDelta:
    """Compare two message dicts and build a validated AttackDelta record.

    Args:
        clean_msg: The clean (unperturbed) message fields.
        attacked_msg: The attacked (perturbed) message fields.
        permitted_fields: Fields that the threat model authorizes changing.
        attack_id: Identifier of the attack specification.
        case_id: Identifier of the case under test.
        corpus_hash: SHA-256 fingerprint of the attack corpus.

    Returns:
        An AttackDelta recording the actual changes found.
    """
    all_keys = sorted(set(clean_msg.keys()) | set(attacked_msg.keys()))
    actual_changes: list[str] = []
    for key in all_keys:
        if clean_msg.get(key) != attacked_msg.get(key):
            actual_changes.append(key)

    return AttackDelta(
        attack_id=attack_id,
        case_id=case_id,
        clean_fields=dict(clean_msg),
        attacked_fields=dict(attacked_msg),
        permitted_changes=tuple(permitted_fields),
        actual_changes=tuple(actual_changes),
        timestamp=datetime.now(timezone.utc).isoformat(),
        corpus_hash=corpus_hash,
    )


def hash_corpus(corpus_dir: str) -> str:
    """SHA-256 hash all JSON attack case files in a corpus directory.

    Files are sorted by name for deterministic ordering.
    MANIFEST.json is excluded from the hash.

    Returns:
        Hex digest string of the combined corpus fingerprint.
    """
    combined = hashlib.sha256()
    if not os.path.isdir(corpus_dir):
        raise FileNotFoundError(f"Corpus directory not found: {corpus_dir}")

    json_files = sorted(
        f
        for f in os.listdir(corpus_dir)
        if f.endswith(".json") and f != "MANIFEST.json"
    )
    if not json_files:
        raise ValueError(f"No JSON attack cases found in {corpus_dir}")

    for fname in json_files:
        path = os.path.join(corpus_dir, fname)
        with open(path, "rb") as fh:
            file_hash = hashlib.sha256(fh.read()).hexdigest()
        combined.update(file_hash.encode("utf-8"))

    return combined.hexdigest()
