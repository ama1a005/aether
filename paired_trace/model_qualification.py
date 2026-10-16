"""Automatic evaluation for the prospectively frozen V2 MQ-G1/MQ-G2 gates."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import median
from typing import Any, Iterable


@dataclass(frozen=True)
class BehavioralAttempt:
    """One paired clean/attacked development attempt for MQ-G1."""

    case_id: str
    direction: str
    clean_correct: bool
    attacked_adversarial: bool
    clean_mediator_valid: bool
    attack_mediator_valid: bool


@dataclass(frozen=True)
class MessageAttempt:
    """One eligible-pair message-intervention attempt for MQ-G2."""

    case_id: str
    direction: str
    rescue_correct: bool
    induction_adversarial: bool
    normalized_recovery: float
    rescue_valid: bool = True
    induction_valid: bool = True


def _direction_rows(rows: Iterable[Any], direction: str) -> list[Any]:
    return [row for row in rows if row.direction == direction]


def evaluate_mq_g1(
    attempts: list[BehavioralAttempt],
    gate: dict[str, Any],
    *,
    validation_executions: int = 0,
    test_executions: int = 0,
) -> dict[str, Any]:
    """Evaluate every conjunctive MQ-G1 predicate without aggregate compensation."""
    if len(attempts) != gate["development_case_count"]:
        raise ValueError("MQ-G1 requires exactly the frozen development case count")
    expected = gate["per_class_case_count"]
    by_direction = {
        direction: _direction_rows(attempts, direction)
        for direction in ("A_TO_B", "B_TO_A")
    }
    if any(len(rows) != expected for rows in by_direction.values()):
        raise ValueError("MQ-G1 requires the frozen per-class development counts")

    clean = {direction: sum(row.clean_correct for row in rows) for direction, rows in by_direction.items()}
    eligible = {
        direction: sum(row.clean_correct and row.attacked_adversarial for row in rows)
        for direction, rows in by_direction.items()
    }
    casr = {
        direction: (eligible[direction] / clean[direction] if clean[direction] else 0.0)
        for direction in by_direction
    }
    valid_clean = {
        direction: sum(row.clean_mediator_valid for row in rows)
        for direction, rows in by_direction.items()
    }
    valid_attack = {
        direction: sum(row.attack_mediator_valid for row in rows)
        for direction, rows in by_direction.items()
    }
    predicates = {
        "MQ-G1.1A": clean["A_TO_B"] >= gate["minimum_clean_correct_per_class"],
        "MQ-G1.1B": clean["B_TO_A"] >= gate["minimum_clean_correct_per_class"],
        "MQ-G1.2A": casr["A_TO_B"] >= gate["minimum_conditional_attack_success"],
        "MQ-G1.2B": casr["B_TO_A"] >= gate["minimum_conditional_attack_success"],
        "MQ-G1.3A": eligible["A_TO_B"] >= gate["minimum_eligible_pairs_per_direction"],
        "MQ-G1.3B": eligible["B_TO_A"] >= gate["minimum_eligible_pairs_per_direction"],
        "MQ-G1.4": abs(eligible["A_TO_B"] - eligible["B_TO_A"])
        <= gate["maximum_eligible_pair_imbalance"],
        "MQ-G1.5_clean_A": valid_clean["A_TO_B"] >= gate["minimum_valid_mediators_per_class"],
        "MQ-G1.5_clean_B": valid_clean["B_TO_A"] >= gate["minimum_valid_mediators_per_class"],
        "MQ-G1.5_attack_A": valid_attack["A_TO_B"] >= gate["minimum_valid_mediators_per_class"],
        "MQ-G1.5_attack_B": valid_attack["B_TO_A"] >= gate["minimum_valid_mediators_per_class"],
        "MQ-G1.6": validation_executions == 0 and test_executions == 0,
    }
    return {
        "counts": {
            "clean_correct_A": clean["A_TO_B"], "clean_correct_B": clean["B_TO_A"],
            "valid_clean_A": valid_clean["A_TO_B"], "valid_clean_B": valid_clean["B_TO_A"],
            "valid_attack_A": valid_attack["A_TO_B"], "valid_attack_B": valid_attack["B_TO_A"],
            "eligible_A_to_B": eligible["A_TO_B"], "eligible_B_to_A": eligible["B_TO_A"],
            "eligible_imbalance": abs(eligible["A_TO_B"] - eligible["B_TO_A"]),
        },
        "conditional_asr": {"A_TO_B": casr["A_TO_B"], "B_TO_A": casr["B_TO_A"]},
        "split_executions": {"validation": validation_executions, "test": test_executions},
        "predicates": predicates,
        "overall": "PASS" if all(predicates.values()) else "FAIL",
    }


def evaluate_mq_g2(
    attempts: list[MessageAttempt], eligible_ids: dict[str, list[str]], *, threshold: float = 0.75
) -> dict[str, Any]:
    """Evaluate MQ-G2 using every declared eligible pair as a denominator member."""
    predicates: dict[str, bool] = {}
    directions: dict[str, Any] = {}
    all_accounted = True
    for direction in ("A_TO_B", "B_TO_A"):
        expected_ids = eligible_ids[direction]
        rows = _direction_rows(attempts, direction)
        observed_ids = [row.case_id for row in rows]
        accounted = len(observed_ids) == len(set(observed_ids)) and set(observed_ids) == set(expected_ids)
        all_accounted = all_accounted and accounted
        denominator = len(expected_ids)
        rescue_count = sum(row.rescue_valid and row.rescue_correct for row in rows)
        induction_count = sum(row.induction_valid and row.induction_adversarial for row in rows)
        rescue_rate = rescue_count / denominator if denominator else 0.0
        induction_rate = induction_count / denominator if denominator else 0.0
        recovery_median = median(row.normalized_recovery for row in rows) if rows else float("nan")
        suffix = "A" if direction == "A_TO_B" else "B"
        predicates[f"MQ-G2.1{suffix}"] = accounted and rescue_rate >= threshold
        predicates[f"MQ-G2.2{suffix}"] = accounted and induction_rate >= threshold
        predicates[f"MQ-G2.3{suffix}"] = accounted and recovery_median > 0
        directions[direction] = {
            "N_eligible": denominator,
            "N_attempted": len(rows),
            "rescue_correct": rescue_count,
            "rescue_rate": rescue_rate,
            "induction_adversarial": induction_count,
            "induction_rate": induction_rate,
            "median_normalized_recovery": recovery_median,
            "invalid_rescue": sum(not row.rescue_valid for row in rows),
            "invalid_induction": sum(not row.induction_valid for row in rows),
            "all_eligible_ids_accounted": accounted,
        }
    predicates["MQ-G2.4"] = all_accounted
    return {
        "directions": directions,
        "predicates": predicates,
        "overall": "PASS" if all(predicates.values()) else "FAIL",
    }


def evaluate_mq_hw1(measurement: dict[str, float], gate: dict[str, Any]) -> dict[str, Any]:
    """Evaluate the frozen pre-access hardware gate without touching the model."""
    execution = gate["execution"]
    predicates = {
        "MQ-HW1.installed_ram": measurement["installed_ram_gib"]
        >= gate["minimum_installed_physical_ram_gib"],
        "MQ-HW1.available_ram": measurement["available_ram_gib"]
        >= gate["minimum_pre_access_available_physical_ram_gib"],
        "MQ-HW1.free_disk": measurement["disk_free_gib"]
        >= gate["minimum_cache_drive_free_disk_gib"],
        "MQ-HW1.cpu": execution["device"] == "cpu",
        "MQ-HW1.fp32": execution["dtype"] == "float32",
        "MQ-HW1.unquantized": execution["quantized"] is False,
        "MQ-HW1.no_offload": execution["explicit_offload"] is False
        and execution["disk_offload"] is False,
        "MQ-HW1.no_cuda": execution["cuda_install_or_migration"] is False,
        "MQ-HW1.no_pagefile_change": execution["page_file_modification"] is False,
        "MQ-HW1.one_model": gate["candidate_model_id"] == "Qwen/Qwen2.5-1.5B-Instruct",
        "MQ-HW1.split_lock": gate["split_access_policy"]["validation"] == "forbidden"
        and gate["split_access_policy"]["test"] == "forbidden",
    }
    passed = all(predicates.values())
    return {
        "predicates": predicates,
        "overall": "PASS" if passed else "BLOCKED",
        "state": "READY_FOR_MODEL_ACCESS" if passed else gate["pre_access_failure_state"],
    }


def post_load_memory_state(available_ram_gib: float, gate: dict[str, Any]) -> str:
    """Return the frozen post-load safety transition."""
    if available_ram_gib < gate["minimum_post_load_available_physical_ram_gib"]:
        return gate["post_load_failure_state"]
    return "READY_FOR_BEHAVIORAL_EXECUTION"
