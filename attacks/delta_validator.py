"""AttackDelta validation and corpus hashing for M2 provenance.

Validates that attack deltas change only permitted fields and provides
corpus-level SHA-256 fingerprinting for reproducibility manifests.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


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
    plan_fingerprint: str = ""


_MISSING = object()


def _canonical(value: Any) -> str:
    """Serialize a JSON-compatible value without platform-dependent spacing."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _changed_paths(clean: Any, attacked: Any, prefix: str = "") -> list[str]:
    """Return changed nested paths while distinguishing absent fields from null."""
    if isinstance(clean, dict) and isinstance(attacked, dict):
        paths: list[str] = []
        for key in sorted(set(clean) | set(attacked)):
            path = f"{prefix}.{key}" if prefix else str(key)
            left, right = clean.get(key, _MISSING), attacked.get(key, _MISSING)
            if left is _MISSING or right is _MISSING:
                paths.append(path)
            else:
                paths.extend(_changed_paths(left, right, path))
        return paths
    return [prefix or "$"] if _canonical(clean) != _canonical(attacked) else []


def _allowed(path: str, permitted: tuple[str, ...]) -> bool:
    """A permission applies to its exact path and descendant paths only."""
    return any(path == item or path.startswith(f"{item}.") for item in permitted)


def validate_delta(delta: AttackDelta, *, require_plan_binding: bool = False) -> tuple[bool, list[str]]:
    """Validate that an AttackDelta conforms to the declared threat model.

    Returns:
        (True, []) if valid; (False, [error_messages]) otherwise.
    """
    errors: list[str] = []

    for field in ("attack_id", "case_id", "corpus_hash"):
        if not getattr(delta, field).strip():
            errors.append(f"{field} must not be blank")
    if require_plan_binding and not delta.plan_fingerprint.strip():
        errors.append("plan_fingerprint must not be blank for campaign evidence")
    recomputed = tuple(_changed_paths(delta.clean_fields, delta.attacked_fields))
    if tuple(delta.actual_changes) != recomputed:
        errors.append("actual_changes does not match canonical nested change set")
    if not delta.actual_changes:
        errors.append("actual_changes is empty; no-op delta is invalid")
    unauthorized = [path for path in delta.actual_changes if not _allowed(path, delta.permitted_changes)]
    if unauthorized:
        errors.append(
            f"over-broad delta: unauthorized field changes {unauthorized}"
        )

    return (len(errors) == 0, errors)


def compute_delta(
    clean_msg: dict[str, Any],
    attacked_msg: dict[str, Any],
    permitted_fields: list[str],
    attack_id: str,
    case_id: str,
    corpus_hash: str,
    *,
    plan_fingerprint: str = "",
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
    return AttackDelta(
        attack_id=attack_id,
        case_id=case_id,
        clean_fields=dict(clean_msg),
        attacked_fields=dict(attacked_msg),
        permitted_changes=tuple(sorted(permitted_fields)),
        actual_changes=tuple(_changed_paths(clean_msg, attacked_msg)),
        timestamp=datetime.now(timezone.utc).isoformat(),
        corpus_hash=corpus_hash,
        plan_fingerprint=plan_fingerprint,
    )


def hash_corpus(corpus_dir: str) -> str:
    """SHA-256 hash all JSON attack case files in a corpus directory.

    Files are sorted by name for deterministic ordering.
    MANIFEST.json is excluded from the hash.

    Returns:
        Hex digest string of the combined corpus fingerprint.
    """
    from attacks.corpus.provenance import compute_corpus_hash
    return compute_corpus_hash(corpus_dir)
