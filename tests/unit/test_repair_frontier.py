"""Pure selection tests; numbers are test fixtures, not experimental results."""

from dataclasses import replace

import pytest

from remediation.selector.frontier import RepairConstraints, RepairMeasurement, select_frontier


def row(name="repair", **updates):
    return replace(RepairMeasurement(name, "message", "unit-test-fixture", "validation", "a" * 64,
                                    0.8, 0.1, 0.95, 0.0, 10.0, 1, 0, 1), **updates)


def test_frontier_retains_security_latency_tradeoff_and_ties():
    rows = [row("quick"), row("safe", asr=0.0, latency_ms=30.0), row("tie"), row("dominated", latency_ms=20.0)]
    result = select_frontier(rows, RepairConstraints(0.2, 0.9, 0.0))
    assert [r.id for r in result.frontier] == ["quick", "safe", "tie"]
    assert result.dominated == ("dominated",)
    assert result == select_frontier(list(reversed(rows)), RepairConstraints(0.2, 0.9, 0.0))


def test_infeasible_candidates_are_excluded_before_pareto_selection():
    rows = [row("unsafe", asr=0.5), row("damaging", benign_utility=0.1), row("errors", failure_rate=0.5),
            row("slow", latency_ms=100.0), row("valid")]
    result = select_frontier(rows, RepairConstraints(0.2, 0.9, 0.1, 50.0))
    assert [r.id for r in result.frontier] == ["valid"]
    assert result.excluded == {"unsafe": ("security_threshold",), "damaging": ("benign_utility_floor",),
                               "errors": ("failure_rate_limit",), "slow": ("latency_limit",)}


def test_different_regions_and_costs_do_not_force_one_repair_location():
    rows = [row("message"), row("sender", region="sender", modified_components=1, modified_message_units=0),
            row("receiver", region="receiver", modified_components=1, modified_message_units=0)]
    assert len(select_frontier(rows, RepairConstraints(0.2, 0.9, 0.0)).frontier) == 3


@pytest.mark.parametrize("update", [{"split": "test"}, {"split": "development"}, {"cohort_sha256": "missing"},
    {"source_run_id": ""}, {"asr": float("nan")}, {"benign_utility": 1.1}, {"extra_forward_passes": -1}])
def test_invalid_or_test_measurements_rejected(update):
    with pytest.raises(ValueError):
        row(**update)


@pytest.mark.parametrize("second", [row("second", cohort_sha256="b" * 64), row("second", baseline_asr=0.7), row()])
def test_incomparable_or_duplicate_measurements_rejected(second):
    with pytest.raises(ValueError):
        select_frontier([row(), second], RepairConstraints(0.2, 0.9, 0.0))


def test_no_feasible_repair_returns_empty_frontier_without_default():
    result = select_frontier([row(asr=0.9)], RepairConstraints(0.2, 0.9, 0.0))
    assert not result.frontier and result.excluded
    assert not select_frontier([], RepairConstraints(0.2, 0.9, 0.0)).frontier
