"""Behavioral tests for the Phase 1 search machinery, independent of models."""

from collections import Counter
from dataclasses import asdict
import json

import pytest

from discovery.budgeted import (Candidate, Evaluation, SearchConfig, matched_random_masks,
                                random_control, receiver_candidates, search)


def measured(score, damage=0.0):
    return Evaluation(score, damage, 2, {"clean": 0.0, "intervened": score})


def test_greedy_recovers_necessary_path_and_verifies_removals():
    candidates = [Candidate("s", "sender"), Candidate("m", "message"),
                  Candidate("r", "receiver"), Candidate("noise", "receiver")]
    calls = []

    def evaluate(mask):
        calls.append(mask)
        return measured(float({"s", "m", "r"} <= set(mask)))

    result = search(candidates, evaluate, SearchConfig())
    assert set(result.retained) == {"s", "m", "r"}
    assert result.one_step_locally_minimal is True
    assert len(calls) == len(set(calls)) == result.queries
    assert result.forward_passes == 2 * result.queries
    assert json.loads(json.dumps(asdict(result)))["feasible"] is True


def test_beam_escapes_a_greedy_interaction_trap():
    candidates = [Candidate(node, "receiver") for node in "abcd"]
    scores = {"abcd": 1.0, "bcd": 1.0, "acd": 0.9, "ac": 0.9, "a": 0.9}
    evaluate = lambda mask: measured(scores.get("".join(mask), 0.0))
    greedy = search(candidates, evaluate, SearchConfig(), method="greedy")
    beam = search(candidates, evaluate, SearchConfig(), method="beam")
    assert greedy.retained == ("b", "c", "d")
    assert beam.retained == ("a",)
    assert beam.one_step_locally_minimal is True


@pytest.mark.parametrize("method", ["greedy", "beam"])
@pytest.mark.parametrize("budget", [1, 2, 3, 5])
def test_budget_includes_baseline_and_never_overruns(method, budget):
    calls = []
    def evaluate(mask):
        calls.append(mask)
        return measured(1.0)
    result = search([Candidate(node, "sender") for node in "abcd"], evaluate,
                    SearchConfig(max_queries=budget), method=method)
    assert len(calls) == result.queries <= budget
    assert result.stop_reason == "query_budget_exhausted"
    assert result.one_step_locally_minimal is None


def test_no_cache_survives_between_runs_and_ties_ignore_input_order():
    candidates = [Candidate(node, "receiver") for node in "cba"]
    config = SearchConfig(max_queries=30)
    result = search(candidates, lambda mask: measured(float(bool(mask))), config)
    reversed_result = search(list(reversed(candidates)), lambda mask: measured(float(bool(mask))), config)
    assert result == reversed_result
    assert result.retained == ("a",)
    failed = search(candidates, lambda mask: measured(0.0), config)
    assert not failed.feasible and failed.one_step_locally_minimal is None


def test_benign_constraint_rejects_a_high_scoring_damaging_mask():
    candidates = [Candidate(node, "receiver") for node in "ab"]
    result = search(candidates, lambda mask: measured(1.0, float(len(mask) < 2)), SearchConfig())
    assert result.retained == ("a", "b")
    assert result.one_step_locally_minimal is True


def test_empty_mask_can_be_valid_without_fabricated_one_node_floor():
    result = search([], lambda mask: measured(1.0), SearchConfig())
    assert result.retained == () and result.queries == 1
    assert result.one_step_locally_minimal is True


@pytest.mark.parametrize("split", ["test", "validation", "train"])
def test_search_rejects_unapproved_splits(split):
    with pytest.raises(ValueError, match="restricted"):
        SearchConfig(split=split)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), True])
def test_nonfinite_or_boolean_measurements_rejected(value):
    with pytest.raises(ValueError):
        measured(value)


def test_evaluator_failure_is_propagated():
    def fail(mask):
        raise RuntimeError("intervention failed")
    with pytest.raises(RuntimeError, match="intervention failed"):
        search([Candidate("a", "receiver")], fail, SearchConfig())


def test_receiver_only_cannot_select_sender_or_mediator():
    candidates = [Candidate("s", "sender"), Candidate("m", "message"), Candidate("r", "receiver")]
    calls = []
    def evaluate(mask):
        calls.append(mask)
        return measured(float("r" in mask))
    result = search(receiver_candidates(candidates), evaluate, SearchConfig())
    assert result.retained == ("r",)
    assert all(set(mask) <= {"r"} for mask in calls)


def test_matched_random_preserves_exact_region_counts_and_seed():
    candidates = [Candidate(f"{region}{i}", region) for region in ("sender", "message", "receiver") for i in range(3)]
    reference = ["sender0", "message0", "receiver0", "receiver1"]
    masks = matched_random_masks(candidates, reference, samples=100, seed=42)
    lookup = {c.id: c.region for c in candidates}
    assert len(masks) == len(set(masks)) == 27
    assert masks == matched_random_masks(list(reversed(candidates)), reference, samples=100, seed=42)
    for mask in masks:
        assert Counter(lookup[node] for node in mask) == {"sender": 1, "message": 1, "receiver": 2}
    result = random_control(candidates, lambda mask: measured(0.0), SearchConfig(max_queries=3),
                            reference, samples=100, seed=42)
    assert result.queries == 3 and not result.feasible
    assert len(result.retained) == 4 and result.one_step_locally_minimal is None


def test_duplicate_candidates_and_unknown_reference_rejected():
    with pytest.raises(ValueError, match="unique"):
        search([Candidate("a", "sender"), Candidate("a", "receiver")], measured, SearchConfig())
    with pytest.raises(ValueError, match="unknown"):
        matched_random_masks([Candidate("a", "sender")], ["missing"], samples=1, seed=0)
