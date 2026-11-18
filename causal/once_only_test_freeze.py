"""Fail-closed validation for the prospective CORE-05 once-only test."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from causal.remediation_freeze import frozen_text_hash_matches


EXPECTED_CASES = tuple(f"v2_case_{index:03d}" for index in range(32, 40))


def load_and_validate_once_only_test_freeze(path: Path, repo: Path) -> dict[str, Any]:
    """Reject test-cohort, method, threshold, budget, attempt, or evidence drift."""
    protocol = yaml.safe_load(path.read_text(encoding="utf-8"))
    if protocol.get("schema_version") != "aether.core05-once-only-test-freeze.v1":
        raise ValueError("Unexpected CORE-05 schema")
    if protocol.get("status") != "AWAITING_HUMAN_REVIEW":
        raise PermissionError("CORE-05 must remain at the human review gate")
    cohort = protocol["cohort"]
    if cohort.get("split") != "test" or tuple(cohort.get("case_ids", ())) != EXPECTED_CASES:
        raise PermissionError("CORE-05 locked test cohort differs")
    if cohort.get("development_case_ids") or cohort.get("validation_case_ids"):
        raise PermissionError("CORE-05 cannot re-execute development or validation")
    registry = (repo / cohort["registry_path"]).resolve()
    if not registry.is_file() or not frozen_text_hash_matches(registry, cohort["registry_sha256"]):
        raise ValueError("CORE-05 case registry hash mismatch")
    arms = protocol["arms"]
    if tuple(row.get("id") for row in arms) != ("no_defense", "frozen_receiver_l20_h5"):
        raise ValueError("CORE-05 arms differ")
    if arms[1].get("component") != "receiver.head.L20.H5.pre_o_proj":
        raise ValueError("CORE-05 selected repair differs")
    rule = protocol["decision_rule"]
    if rule.get("no_arm_reselection") is not True or rule.get("no_threshold_relaxation_after_execution") is not True:
        raise PermissionError("CORE-05 cannot reselect or relax thresholds")
    if rule.get("test_acceptance") != {"minimum_attacked_decision_recovery_accuracy": 0.75,
                                       "minimum_clean_decision_accuracy": 1.0,
                                       "maximum_invalid_or_error_fraction": 0.0}:
        raise ValueError("CORE-05 thresholds differ")
    attempt = protocol["attempt_control"]
    if attempt.get("once_only") is not True or attempt.get("attempt_marker_required_before_model_access") is not True:
        raise PermissionError("CORE-05 once-only guard differs")
    if attempt.get("fresh_rerun_after_complete_attempt") != "forbidden":
        raise PermissionError("CORE-05 complete test cannot be rerun")
    budget = protocol["budget"]
    if budget.get("maximum_model_forward_steps_total") != 504 or budget.get("maximum_model_forward_steps_per_seed") != 168:
        raise ValueError("CORE-05 budget differs")
    semantics = protocol["intervention_semantics"]
    if semantics.get("donor") != "same_case_paired_clean_condition" or semantics.get("deployable_without_oracle") is not False:
        raise ValueError("CORE-05 oracle dependency differs")
    locks = protocol["split_locks"]
    if locks.get("development_execution") != "forbidden" or locks.get("validation_execution") != "forbidden":
        raise PermissionError("CORE-05 protected split lock differs")
    review = protocol["review"]
    if review.get("implementation_before_approval") != "forbidden" or review.get("model_access_before_approval") != "forbidden":
        raise PermissionError("CORE-05 must await exact-hash approval")
    for record in protocol["evidence_inputs"].values():
        evidence = (repo / record["path"]).resolve()
        if not evidence.is_file() or not frozen_text_hash_matches(evidence, record["sha256"]):
            raise ValueError(f"CORE-05 evidence hash mismatch: {record['path']}")
    return protocol

