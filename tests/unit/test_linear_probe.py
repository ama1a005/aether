"""Probe tests use synthetic arrays and are not experimental evidence."""

from dataclasses import replace

import numpy as np
import pytest

from evaluation.linear_probe import (ProbeData, binary_probe_metrics, evaluate_probe,
                                     fit_linear_probe, permutation_controls)


def data(features, labels, prefix, split="development"):
    values = np.asarray(features)
    return ProbeData(values, np.asarray(labels),
                     tuple(f"{prefix}-{index}" for index in range(len(labels))),
                     tuple(f"feature-{index}" for index in range(values.shape[1])), split)


def test_probe_fits_separable_development_holdout_deterministically():
    fit = data([[-3, 9], [-2, 9], [-1, 9], [1, 9], [2, 9], [3, 9]], [0, 0, 0, 1, 1, 1], "fit")
    holdout = data([[-4, 100], [-0.5, -100], [0.5, 50], [4, -50]], [0, 0, 1, 1], "eval")
    first = fit_linear_probe(fit)
    second = fit_linear_probe(fit)
    metrics = evaluate_probe(first, fit, holdout)
    assert np.array_equal(first.weights, second.weights)
    assert metrics.auroc == metrics.pr_auc == metrics.accuracy_at_half == 1.0
    assert first.scale[1] == 1.0  # train-constant feature cannot leak holdout scaling


def test_tie_aware_metrics_match_known_values():
    metrics = binary_probe_metrics([0, 1, 0, 1], [0.5, 0.5, 0.5, 0.5])
    assert metrics.auroc == 0.5
    assert metrics.pr_auc == pytest.approx((0.5 + 0.5) / 2)
    assert metrics.accuracy_at_half == 0.5
    reordered = binary_probe_metrics([1, 1, 0, 0], [0.5, 0.5, 0.5, 0.5])
    assert reordered.pr_auc == metrics.pr_auc


def test_probe_owns_read_only_array_copies():
    source = np.asarray([[-1.0], [1.0]])
    fit = data(source, [0, 1], "fit")
    source[0, 0] = 100
    assert fit.features[0, 0] == -1
    with pytest.raises(ValueError, match="read-only"):
        fit.features[0, 0] = 10


def test_feature_provenance_must_match():
    fit = data([[-1], [1]], [0, 1], "fit")
    evaluation = replace(data([[-2], [2]], [0, 1], "eval"), feature_ids=("different",))
    with pytest.raises(ValueError, match="feature provenance"):
        evaluate_probe(fit_linear_probe(fit), fit, evaluation)


def test_fit_and_evaluation_ids_must_be_disjoint():
    fit = data([[-1], [1]], [0, 1], "same")
    with pytest.raises(ValueError, match="overlap"):
        evaluate_probe(fit_linear_probe(fit), fit, fit)


@pytest.mark.parametrize("fit_split,eval_split", [("validation", "development"), ("development", "test"),
                                                    ("development", "validation")])
def test_default_protocol_rejects_locked_or_unexpected_splits(fit_split, eval_split):
    fit = data([[-1], [1]], [0, 1], "fit", fit_split)
    evaluation = data([[-2], [2]], [0, 1], "eval", eval_split)
    with pytest.raises(PermissionError):
        probe = fit_linear_probe(fit)
        evaluate_probe(probe, fit, evaluation)


def test_probe_provenance_must_match_fit_data():
    fit = data([[-1], [1]], [0, 1], "fit")
    other = data([[-2], [2]], [0, 1], "other")
    evaluation = data([[-3], [3]], [0, 1], "eval")
    with pytest.raises(ValueError, match="provenance"):
        evaluate_probe(fit_linear_probe(fit), other, evaluation)


def test_permutation_controls_are_seeded_unique_and_do_not_mutate_labels():
    fit = data([[-3], [-2], [-1], [1], [2], [3]], [0, 0, 0, 1, 1, 1], "fit")
    evaluation = data([[-4], [-0.5], [0.5], [4]], [0, 0, 1, 1], "eval")
    original = fit.labels.copy()
    assert permutation_controls(fit, evaluation, seeds=[1, 2]) == permutation_controls(fit, evaluation, seeds=[1, 2])
    assert np.array_equal(fit.labels, original)
    with pytest.raises(ValueError, match="unique"):
        permutation_controls(fit, evaluation, seeds=[1, 1])


@pytest.mark.parametrize("features,labels", [([[float("nan")], [1]], [0, 1]),
                                               ([[0], [1]], [0, 2]),
                                               ([[0]], [0])])
def test_invalid_probe_data_fails_closed(features, labels):
    with pytest.raises(ValueError):
        data(features, labels, "bad")


def test_single_class_fit_and_metrics_are_rejected():
    one_class = data([[0], [1]], [0, 0], "fit")
    with pytest.raises(ValueError, match="both classes"):
        fit_linear_probe(one_class)
    with pytest.raises(ValueError, match="both binary classes"):
        binary_probe_metrics([0, 0], [0.1, 0.2])
