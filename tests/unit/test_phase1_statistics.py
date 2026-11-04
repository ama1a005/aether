import pytest

from evaluation.phase1_statistics import OutcomeRecord, paired_method_comparison, summarize_outcomes


def row(case, seed, method, success, *, valid=True):
    return OutcomeRecord(case, seed, method, "family", True, True, success, valid,
                         None if valid else "TimeoutError", .9 if valid else None,
                         .1 if valid else None, 4)


def test_complete_statistics_keep_errors_and_seed_variation():
    records = [row("a", 0, "full", True), row("b", 0, "full", False, valid=False),
               row("a", 1, "full", False), row("b", 1, "full", False),
               row("a", 0, "receiver", False), row("b", 0, "receiver", False),
               row("a", 1, "receiver", False), row("b", 1, "receiver", False)]
    summary = summarize_outcomes(records, bootstrap_samples=100)
    assert summary["full"]["eligible"] == 4
    assert summary["full"]["successes"] == 1
    assert summary["full"]["invalid_or_error"] == 1
    assert summary["full"]["seed_count"] == 2
    paired = paired_method_comparison(records, "full", "receiver")
    assert paired["left_only"] == 1 and paired["right_only"] == 0
    assert paired["eligible_pairs"] == 4


def test_statistics_reject_duplicates_and_pair_mismatch():
    item = row("a", 0, "full", True)
    with pytest.raises(ValueError, match="unique"):
        summarize_outcomes([item, item])
    with pytest.raises(ValueError, match="identical"):
        paired_method_comparison([item, row("b", 0, "receiver", False)], "full", "receiver")
