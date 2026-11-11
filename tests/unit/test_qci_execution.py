"""Tests for frozen QCI-1.1 execution and classification rules."""

from __future__ import annotations

import pytest

from causal.qci_execution import (
    QueryLedger, assess_candidate, induction_effect, parse_candidate,
    rescue_effect, shuffled_donor_mapping,
)


THRESHOLDS = {
    "median_rescue_min": 0.5,
    "rescue_above_0_25_fraction_min": 0.75,
    "median_induction_min": 0.5,
    "induction_above_0_25_fraction_min": 0.75,
    "paired_minus_shuffled_median_min": 0.2,
    "paired_minus_irrelevant_position_min": 0.2,
    "all_raw_effects_expected_direction": True,
}


def test_candidate_parser_preserves_region_and_exact_site() -> None:
    module = parse_candidate({"candidate_id": "module.L22.mlp_output", "agent": "sender", "family": "module"})
    head = parse_candidate({"candidate_id": "head.L20.H5.pre_o_proj", "agent": "receiver", "family": "head"})
    assert (module.layer, module.component_type, module.head) == (22, "mlp_output", None)
    assert (head.layer, head.component_type, head.head) == (20, None, 5)
    with pytest.raises(ValueError, match="invalid QCI head"):
        parse_candidate({"candidate_id": "head.L20.post_proj.H5", "agent": "receiver", "family": "head"})


def test_shuffled_mapping_is_direction_matched_deterministic_and_not_self() -> None:
    rows = [
        {"case_id": f"a{i}", "direction": "A_TO_B"} for i in range(3)
    ] + [{"case_id": f"b{i}", "direction": "B_TO_A"} for i in range(3)]
    first = shuffled_donor_mapping(rows)
    assert first == shuffled_donor_mapping(reversed(rows))
    assert all(case_id != donor for case_id, donor in first.items())
    assert all(first[f"a{i}"].startswith("a") and first[f"b{i}"].startswith("b") for i in range(3))


def test_budget_and_normalized_effects_fail_closed() -> None:
    ledger = QueryLedger(2, 3)
    ledger.charge(forward_steps=2)
    ledger.charge(forward_steps=1)
    with pytest.raises(RuntimeError, match="execution"):
        ledger.charge()
    assert rescue_effect(2.0, 0.0, 1.0) == 0.5
    assert induction_effect(2.0, 0.0, 1.0) == 0.5
    with pytest.raises(ValueError, match="degenerate"):
        rescue_effect(1.0, 1.0, 1.0)


def _rows(rescue: float = 0.8, induction: float = 0.8, shuffled: float = 0.1) -> list[dict[str, object]]:
    values = {
        "paired_rescue": rescue, "paired_induction": induction,
        "shuffled_donor_rescue": shuffled, "irrelevant_position_rescue": 0.1,
        "identity_clean_to_clean": 0.0, "identity_attacked_to_attacked": 0.0,
        "passive_hook": 0.0,
    }
    rows = []
    for operator, value in values.items():
        for index in range(16):
            rows.append({
                "candidate_id": "module.L22.mlp_output", "case_id": str(index),
                "operator": operator, "status": "ok", "normalized_effect": value,
                "noninterference_pass": operator not in {
                    "paired_rescue", "paired_induction", "shuffled_donor_rescue",
                    "irrelevant_position_rescue",
                },
            })
    return rows


def test_support_requires_effect_specificity_and_noninterference() -> None:
    accepted = assess_candidate(_rows(), THRESHOLDS)
    assert accepted["status"] == "supported"
    rejected = assess_candidate(_rows(shuffled=0.7), THRESHOLDS)
    assert rejected["status"] == "rejected"
    assert "shuffled_separation" in rejected["reasons"]
    broken = _rows()
    broken[-1]["noninterference_pass"] = False
    assert "control_noninterference" in assess_candidate(broken, THRESHOLDS)["reasons"]
    failed = _rows()
    failed[0]["status"] = "invalid_sender_output"
    assessment = assess_candidate(failed, THRESHOLDS)
    assert assessment["status"] == "rejected"
    assert assessment["failed_execution_count"] == 1
