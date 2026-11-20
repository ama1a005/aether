"""Corpus provenance, integrity verification, and completeness auditing.

Provides deterministic SHA-256 fingerprinting of attack corpora for
reproducibility manifests and fail-closed integrity checks.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Tuple


def compute_corpus_hash(corpus_dir: str) -> str:
    """Compute a deterministic SHA-256 fingerprint of all attack case files.

    Lists all .json files (excluding MANIFEST.json), sorted by name,
    hashes each file's bytes individually, then combines all individual
    hashes into a single corpus fingerprint.

    Args:
        corpus_dir: Path to the attack cases directory.

    Returns:
        Hex digest of the combined corpus fingerprint.

    Raises:
        FileNotFoundError: If corpus_dir does not exist.
        ValueError: If no JSON case files are found.
    """
    if not os.path.isdir(corpus_dir):
        raise FileNotFoundError(f"Corpus directory not found: {corpus_dir}")

    json_files = sorted(
        f
        for f in os.listdir(corpus_dir)
        if f.endswith(".json") and f != "MANIFEST.json"
    )
    if not json_files:
        raise ValueError(f"No JSON attack cases found in {corpus_dir}")

    combined = hashlib.sha256()

    for fname in json_files:
        path = os.path.join(corpus_dir, fname)
        with open(path, "rb") as fh:
            digest = hashlib.sha256(fh.read()).hexdigest()
        combined.update(digest.encode("utf-8"))

    return combined.hexdigest()


def compute_file_hashes(corpus_dir: str) -> dict[str, str]:
    """Return individual SHA-256 hashes for each attack case file.

    Args:
        corpus_dir: Path to the attack cases directory.

    Returns:
        Dict mapping filename to its hex SHA-256 digest.
    """
    if not os.path.isdir(corpus_dir):
        raise FileNotFoundError(f"Corpus directory not found: {corpus_dir}")

    json_files = sorted(
        f
        for f in os.listdir(corpus_dir)
        if f.endswith(".json") and f != "MANIFEST.json"
    )
    result: dict[str, str] = {}
    for fname in json_files:
        path = os.path.join(corpus_dir, fname)
        with open(path, "rb") as fh:
            result[fname] = hashlib.sha256(fh.read()).hexdigest()
    return result


def generate_provenance_manifest(
    corpus_dir: str, seed: int, families: list[str]
) -> dict[str, Any]:
    """Generate a complete provenance manifest for an attack corpus.

    Args:
        corpus_dir: Path to the attack cases directory.
        seed: Random seed used for corpus generation.
        families: List of expected attack families.

    Returns:
        Dict with corpus_hash, file_count, families, seed,
        generation_timestamp, and individual file_hashes.
    """
    corpus_hash = compute_corpus_hash(corpus_dir)
    file_hashes = compute_file_hashes(corpus_dir)

    return {
        "corpus_hash": corpus_hash,
        "file_count": len(file_hashes),
        "families": sorted(families),
        "seed": seed,
        "generation_timestamp": datetime.now(timezone.utc).isoformat(),
        "file_hashes": file_hashes,
    }


def verify_corpus_integrity(
    corpus_dir: str, expected_hash: str
) -> Tuple[bool, str]:
    """Verify that the corpus has not been modified since the hash was recorded.

    Args:
        corpus_dir: Path to the attack cases directory.
        expected_hash: Previously recorded SHA-256 corpus fingerprint.

    Returns:
        (True, "OK") if hashes match;
        (False, "Mismatch: expected X got Y") otherwise.
    """
    actual_hash = compute_corpus_hash(corpus_dir)
    if actual_hash == expected_hash:
        return (True, "OK")
    return (False, f"Mismatch: expected {expected_hash} got {actual_hash}")


def audit_corpus_completeness(
    corpus_dir: str, expected_families: list[str], min_per_family: int
) -> Tuple[bool, List[str]]:
    """Audit that the corpus has sufficient coverage of each attack family.

    Loads each JSON case file, counts cases per family, and checks
    every expected family has at least min_per_family cases.

    Args:
        corpus_dir: Path to the attack cases directory.
        expected_families: List of required attack families.
        min_per_family: Minimum number of cases required per family.

    Returns:
        (True, []) if audit passes;
        (False, [error_messages]) otherwise.
    """
    if not os.path.isdir(corpus_dir):
        return (False, [f"Corpus directory not found: {corpus_dir}"])

    json_files = sorted(
        f
        for f in os.listdir(corpus_dir)
        if f.endswith(".json") and f != "MANIFEST.json"
    )

    family_counts: dict[str, int] = {}
    for fname in json_files:
        path = os.path.join(corpus_dir, fname)
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        family = data.get("family", "unknown")
        family_counts[family] = family_counts.get(family, 0) + 1

    errors: list[str] = []
    for family in expected_families:
        count = family_counts.get(family, 0)
        if count < min_per_family:
            errors.append(
                f"Family '{family}' has {count} cases, "
                f"requires at least {min_per_family}"
            )

    return (len(errors) == 0, errors)
