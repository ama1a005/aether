"""Tests for the frozen V2 model-qualification gate semantics."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from paired_trace.model_qualification import (
    BehavioralAttempt, MessageAttempt, evaluate_mq_g1, evaluate_mq_g2,
    evaluate_mq_hw1, post_load_memory_state,
)


GATE = json.loads(Path("configs/model_qualification/v2_mq_g1.json").read_text(encoding="utf-8"))
HW_GATE = json.loads(Path("configs/model_qualification/v2_mq_hw1.json").read_text(encoding="utf-8"))


def _behavioral(
    *, clean_a: int = 12, clean_b: int = 12, eligible_a: int = 9, eligible_b: int = 9,
    valid_clean_a: int = 12, valid_clean_b: int = 12,
    valid_attack_a: int = 12, valid_attack_b: int = 12,
) -> list[BehavioralAttempt]:
    rows = []
    for direction, clean, eligible, vc, va in (
        ("A_TO_B", clean_a, eligible_a, valid_clean_a, valid_attack_a),
        ("B_TO_A", clean_b, eligible_b, valid_clean_b, valid_attack_b),
    ):
        for index in range(12):
            rows.append(BehavioralAttempt(
                case_id=f"{direction}-{index}", direction=direction,
                clean_correct=index < clean,
                attacked_adversarial=index < eligible,
                clean_mediator_valid=index < vc,
                attack_mediator_valid=index < va,
            ))
    return rows


def test_conditional_asr_excludes_clean_incorrect_from_both_terms() -> None:
    result = evaluate_mq_g1(_behavioral(clean_a=10, eligible_a=8), GATE)
    assert result["conditional_asr"]["A_TO_B"] == pytest.approx(0.8)
    assert result["counts"]["eligible_A_to_B"] == 8


def test_per_class_competence_is_not_compensated_by_other_class() -> None:
    result = evaluate_mq_g1(_behavioral(clean_a=12, clean_b=9), GATE)
    assert result["predicates"]["MQ-G1.1A"] is True
    assert result["predicates"]["MQ-G1.1B"] is False
    assert result["overall"] == "FAIL"


def test_eligibility_requires_clean_correct_and_adversarial_attack() -> None:
    rows = _behavioral(clean_a=10, eligible_a=8)
    rows[10] = BehavioralAttempt("A_TO_B-10", "A_TO_B", False, True, True, True)
    result = evaluate_mq_g1(rows, GATE)
    assert result["counts"]["eligible_A_to_B"] == 8


def test_directional_imbalance_is_conjunctive() -> None:
    result = evaluate_mq_g1(_behavioral(eligible_a=11, eligible_b=8), GATE)
    assert result["predicates"]["MQ-G1.4"] is False
    assert result["overall"] == "FAIL"


def test_each_mediator_validity_cell_must_pass() -> None:
    result = evaluate_mq_g1(_behavioral(valid_attack_b=10), GATE)
    assert result["predicates"]["MQ-G1.5_attack_B"] is False
    assert result["overall"] == "FAIL"


def test_validation_or_test_access_fails_split_guard() -> None:
    assert evaluate_mq_g1(_behavioral(), GATE, validation_executions=1)["overall"] == "FAIL"
    assert evaluate_mq_g1(_behavioral(), GATE, test_executions=1)["predicates"]["MQ-G1.6"] is False


def _messages(rescue: int = 6, induction: int = 6, recovery: float = 0.2) -> tuple[list[MessageAttempt], dict[str, list[str]]]:
    rows = []
    ids = {}
    for direction in ("A_TO_B", "B_TO_A"):
        ids[direction] = [f"{direction}-{index}" for index in range(8)]
        rows.extend(MessageAttempt(case_id, direction, index < rescue, index < induction, recovery)
                    for index, case_id in enumerate(ids[direction]))
    return rows, ids


def test_mq_g2_rescue_induction_and_median_direction() -> None:
    rows, ids = _messages()
    result = evaluate_mq_g2(rows, ids)
    assert result["overall"] == "PASS"
    assert result["directions"]["A_TO_B"]["rescue_rate"] == 0.75
    assert result["directions"]["B_TO_A"]["induction_rate"] == 0.75


def test_mq_g2_nonpositive_median_fails() -> None:
    rows, ids = _messages(recovery=0.0)
    result = evaluate_mq_g2(rows, ids)
    assert result["predicates"]["MQ-G2.3A"] is False
    assert result["overall"] == "FAIL"


def test_mq_g2_missing_or_invalid_runs_are_not_silently_excluded() -> None:
    rows, ids = _messages()
    assert evaluate_mq_g2(rows[:-1], ids)["predicates"]["MQ-G2.4"] is False
    rows[0] = MessageAttempt(rows[0].case_id, rows[0].direction, True, True, 0.2, rescue_valid=False)
    result = evaluate_mq_g2(rows, ids)
    assert result["directions"]["A_TO_B"]["invalid_rescue"] == 1
    assert result["directions"]["A_TO_B"]["rescue_rate"] == 5 / 8


def test_mq_hw1_thresholds_are_inclusive_and_conjunctive() -> None:
    measurement = {"installed_ram_gib": 15.0, "available_ram_gib": 10.5, "disk_free_gib": 12.0}
    assert evaluate_mq_hw1(measurement, HW_GATE)["overall"] == "PASS"
    measurement["available_ram_gib"] = 10.499
    assert evaluate_mq_hw1(measurement, HW_GATE)["state"] == "BLOCKED_PRE_ACCESS"


def test_mq_hw1_disk_threshold_blocks_independently() -> None:
    result = evaluate_mq_hw1(
        {"installed_ram_gib": 15.67, "available_ram_gib": 12.0, "disk_free_gib": 11.99}, HW_GATE
    )
    assert result["predicates"]["MQ-HW1.free_disk"] is False
    assert result["overall"] == "BLOCKED"


def test_mq_hw1_post_load_memory_threshold() -> None:
    assert post_load_memory_state(2.0, HW_GATE) == "READY_FOR_BEHAVIORAL_EXECUTION"
    assert post_load_memory_state(1.999, HW_GATE) == "BLOCKED_AFTER_LOAD"


def test_mq_hw1_freezes_one_unquantized_fp32_cpu_model_and_split_locks() -> None:
    result = evaluate_mq_hw1(
        {"installed_ram_gib": 16.0, "available_ram_gib": 11.0, "disk_free_gib": 13.0}, HW_GATE
    )
    for predicate in ("MQ-HW1.one_model", "MQ-HW1.unquantized", "MQ-HW1.fp32",
                      "MQ-HW1.cpu", "MQ-HW1.split_lock"):
        assert result["predicates"][predicate] is True
