"""Fail-closed validation for the prospective CORE-04 validation protocol."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from causal.remediation_freeze import frozen_text_hash_matches


EXPECTED_CASES = tuple(f"v2_case_{index:03d}" for index in range(24, 32))
EXPECTED_ARMS = ("no_defense", "frozen_receiver_l20_h5")
EXPECTED_COMPONENT = "receiver.head.L20.H5.pre_o_proj"


def load_and_validate_locked_validation_freeze(path: Path, repo: Path) -> dict[str, Any]:
    """Load CORE-04 and reject selection, split, budget, or provenance drift."""
    protocol = yaml.safe_load(path.read_text(encoding="utf-8"))
    if protocol.get("schema_version") != "aether.core04-locked-validation-freeze.v1":
        raise ValueError("Unexpected CORE-04 schema")
    if protocol.get("status") != "AWAITING_HUMAN_REVIEW":
        raise PermissionError("CORE-04 must remain at the human review gate")

    cohort = protocol["cohort"]
    if cohort.get("split") != "validation" or tuple(cohort.get("case_ids", ())) != EXPECTED_CASES:
        raise PermissionError("CORE-04 locked validation cohort differs")
    if cohort.get("development_case_ids") or cohort.get("test_case_ids"):
        raise PermissionError("CORE-04 cannot execute development or test cases")
    registry = (repo / cohort["registry_path"]).resolve()
    if not registry.is_relative_to(repo.resolve()) or not registry.is_file():
        raise ValueError("CORE-04 case registry is missing")
    if not frozen_text_hash_matches(registry, cohort["registry_sha256"]):
        raise ValueError("CORE-04 case registry hash mismatch")

    arms = protocol["arms"]
    if tuple(arm.get("id") for arm in arms) != EXPECTED_ARMS:
        raise ValueError("CORE-04 arm set or order differs")
    if arms[1].get("component") != EXPECTED_COMPONENT:
        raise ValueError("CORE-04 selected receiver component differs")
    decision = protocol["decision_rule"]
    if decision.get("no_arm_reselection") is not True:
        raise PermissionError("CORE-04 cannot reselect a repair on validation")
    if decision.get("no_threshold_relaxation_after_execution") is not True:
        raise PermissionError("CORE-04 thresholds must remain frozen")

    for endpoint in (protocol["endpoints"]["primary_security"],
                     protocol["endpoints"]["primary_clean_utility"]):
        if endpoint.get("denominator") != "all_8_predeclared_cases_including_invalid_and_error_rows":
            raise ValueError("CORE-04 endpoint drops protected validation rows")
    benign = protocol["endpoints"]["benign_damage"]
    if benign.get("units") != "raw_A_minus_B_logit_margin":
        raise ValueError("CORE-04 benign-damage units differ")

    semantics = protocol["intervention_semantics"]
    if semantics.get("donor") != "same_case_paired_clean_condition":
        raise ValueError("CORE-04 must disclose its paired clean donor")
    if semantics.get("deployable_without_oracle") is not False:
        raise ValueError("CORE-04 cannot claim an oracle-free defense")

    budget = protocol["budget"]
    if budget.get("per_case_forward_steps") != {"no_defense": 10, "frozen_receiver_l20_h5": 11}:
        raise ValueError("CORE-04 per-case forward accounting differs")
    if budget.get("maximum_model_forward_steps_per_seed") != 168:
        raise ValueError("CORE-04 per-seed budget differs")
    if budget.get("maximum_model_forward_steps_total") != 504:
        raise ValueError("CORE-04 total budget differs")

    locks = protocol["split_locks"]
    if locks.get("development_execution") != "forbidden" or locks.get("test_execution") != "forbidden":
        raise PermissionError("CORE-04 protected split lock differs")
    review = protocol["review"]
    if review.get("implementation_before_approval") != "forbidden" or review.get("model_access_before_approval") != "forbidden":
        raise PermissionError("CORE-04 implementation and model access must await approval")

    for record in protocol["evidence_inputs"].values():
        evidence = (repo / record["path"]).resolve()
        if not evidence.is_relative_to(repo.resolve()) or not evidence.is_file():
            raise ValueError(f"Missing CORE-04 evidence input: {record['path']}")
        if not frozen_text_hash_matches(evidence, record["sha256"]):
            raise ValueError(f"CORE-04 evidence hash mismatch: {record['path']}")
    return protocol

