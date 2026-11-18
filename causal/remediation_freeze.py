"""Fail-closed validation for the prospective CORE-03 remediation protocol."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import yaml


EXPECTED_CASES = ("v2_case_010", "v2_case_011", "v2_case_012", "v2_case_013")
EXPECTED_ARMS = (
    "no_defense",
    "fixed_message_whole",
    "fixed_receiver_l22_attention",
    "mechanism_message_decision_code",
    "mechanism_receiver_l20_h5",
)


def sha256_file(path: Path) -> str:
    """Return the hexadecimal SHA-256 of one file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def frozen_text_hash_matches(path: Path, expected: str) -> bool:
    """Accept an exact hash or newline-only Git conversion for UTF-8 text evidence."""
    raw = path.read_bytes()
    variants = {hashlib.sha256(raw).hexdigest()}
    if path.suffix.lower() in {".json", ".jsonl", ".yaml", ".yml", ".md", ".txt"}:
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError:
            return expected in variants
        canonical_lf = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        canonical_crlf = canonical_lf.replace(b"\n", b"\r\n")
        variants.update({hashlib.sha256(canonical_lf).hexdigest(),
                         hashlib.sha256(canonical_crlf).hexdigest()})
    return expected in variants


def load_and_validate_remediation_freeze(path: Path, repo: Path) -> dict[str, Any]:
    """Load CORE-03 and reject scientific, split, budget, or provenance drift."""
    protocol = yaml.safe_load(path.read_text(encoding="utf-8"))
    if protocol.get("schema_version") != "aether.core03-remediation-freeze.v1":
        raise ValueError("Unexpected CORE-03 schema")
    if protocol.get("status") != "AWAITING_HUMAN_REVIEW":
        raise PermissionError("CORE-03 proposal must remain at the human review gate")

    cohort = protocol["cohort"]
    if tuple(cohort.get("case_ids", ())) != EXPECTED_CASES:
        raise PermissionError("CORE-03 development-audit cohort differs")
    if cohort.get("validation_case_ids") or cohort.get("test_case_ids"):
        raise PermissionError("CORE-03 cannot access validation or test cases")

    arms = tuple(row.get("id") for row in protocol["arms"])
    if arms != EXPECTED_ARMS:
        raise ValueError("CORE-03 arm set or order differs")
    semantics = protocol["intervention_semantics"]
    if semantics.get("donor") != "same_case_paired_clean_condition":
        raise ValueError("CORE-03 must use the paired clean donor")
    if semantics.get("deployable_without_oracle") is not False:
        raise ValueError("CORE-03 cannot claim a deployable oracle-free defense")
    if semantics.get("overlap_policy") != "one_arm_per_execution_no_composed_interventions":
        raise ValueError("CORE-03 overlap semantics differ")

    security = protocol["endpoints"]["primary_security"]
    utility = protocol["endpoints"]["primary_clean_utility"]
    for endpoint in (security, utility):
        if endpoint.get("denominator") != "all_predeclared_cases_including_invalid_and_error_rows":
            raise ValueError("CORE-03 endpoint silently drops invalid or error rows")
    benign = protocol["endpoints"]["benign_damage"]
    if benign.get("units") != "raw_A_minus_B_logit_margin":
        raise ValueError("CORE-03 benign-damage units differ")
    if "not_benign_accuracy" not in benign.get("interpretation", ""):
        raise ValueError("CORE-03 must distinguish margin damage from clean accuracy")

    budget = protocol["budget"]
    per_case = budget["per_case_forward_steps"]
    if tuple(per_case) != EXPECTED_ARMS or sum(per_case.values()) != 52:
        raise ValueError("CORE-03 per-case forward accounting differs")
    if budget.get("maximum_model_forward_steps_per_seed") != 208:
        raise ValueError("CORE-03 per-seed budget differs")
    if budget.get("maximum_model_forward_steps_total") != 624:
        raise ValueError("CORE-03 total budget differs")

    locks = protocol["split_locks"]
    if locks.get("validation_execution") != "forbidden" or locks.get("test_execution") != "forbidden":
        raise PermissionError("CORE-03 protected split lock differs")
    if protocol["review"].get("model_access_before_approval") != "forbidden":
        raise PermissionError("CORE-03 model access must await exact-hash approval")

    for record in protocol["evidence_inputs"].values():
        evidence = (repo / record["path"]).resolve()
        if not evidence.is_relative_to(repo.resolve()) or not evidence.is_file():
            raise ValueError(f"Missing CORE-03 evidence input: {record['path']}")
        if not frozen_text_hash_matches(evidence, record["sha256"]):
            raise ValueError(f"CORE-03 evidence hash mismatch: {record['path']}")
    return protocol

