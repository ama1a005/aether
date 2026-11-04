"""Measured evaluator wiring tests use executed deterministic toy scores."""
import pytest

from discovery.budgeted import Candidate, SearchConfig, receiver_candidates, search
from discovery.evaluator import CaseMeasurement, MeasuredMaskEvaluator


CANDIDATES = (Candidate("S", "sender"), Candidate("SN", "sender"),
              Candidate("M", "message"), Candidate("MN", "message"),
              Candidate("R", "receiver"), Candidate("RN", "receiver"))


def execute(case_id, mask):
    active = set(mask)
    circuit = float({"S", "M", "R"} <= active)
    return CaseMeasurement(case_id, 1.0, circuit, 0.0,
                           0.1 if "RN" in active else 0.0, 4,
                           {"case": case_id, "mask": mask, "score": circuit})


def test_full_and_receiver_scopes_share_executed_cohort_and_raw_rows():
    config = SearchConfig(max_queries=32, faithfulness_threshold=.99,
                          max_benign_damage=.2, split="synthetic")
    full = search(CANDIDATES, MeasuredMaskEvaluator(["a", "b"], execute), config)
    assert full.retained == ("M", "R", "S")
    assert full.evaluation.forward_passes == 8
    assert len(full.evaluation.raw_outputs["cases"]) == 2

    receivers = receiver_candidates(CANDIDATES)
    fixed = [item.id for item in CANDIDATES if item.region != "receiver"]
    receiver = search(receivers, MeasuredMaskEvaluator(["a", "b"], execute,
                      fixed_retained=fixed), config)
    assert receiver.feasible and receiver.retained == ("R",)
    assert receiver.evaluation.raw_outputs["fixed_retained"] == sorted(fixed)


def test_measurement_failures_are_not_dropped():
    evaluator = MeasuredMaskEvaluator(["a", "b"],
        lambda case_id, mask: execute("wrong" if case_id == "b" else case_id, mask))
    with pytest.raises(ValueError, match="wrong case"):
        evaluator(("S", "M", "R"))
    with pytest.raises(ValueError, match="scores"):
        CaseMeasurement("a", float("nan"), 0, 0, 0, 1, {"raw": True})
