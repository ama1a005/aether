"""Simple leakage-resistant linear activation probe for correlation baselines.

Predictive probe performance is correlational evidence. It is never converted
into a causal edge or used as a substitute for an intervention.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Sequence

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit
from scipy.stats import rankdata


@dataclass(frozen=True)
class ProbeData:
    """Activation features, binary labels, immutable identities and split name."""

    features: np.ndarray
    labels: np.ndarray
    sample_ids: tuple[str, ...]
    feature_ids: tuple[str, ...]
    split: str

    def __post_init__(self) -> None:
        features = np.asarray(self.features)
        labels = np.asarray(self.labels)
        if features.ndim != 2 or labels.ndim != 1 or features.shape[0] != labels.shape[0]:
            raise ValueError("Features must be [samples, features] and labels [samples]")
        if features.shape[0] < 2 or features.shape[1] < 1:
            raise ValueError("Probe data requires at least two samples and one feature")
        if len(self.sample_ids) != features.shape[0] or len(set(self.sample_ids)) != len(self.sample_ids):
            raise ValueError("Sample ids must be unique and align with feature rows")
        if len(self.feature_ids) != features.shape[1] or len(set(self.feature_ids)) != len(self.feature_ids):
            raise ValueError("Feature ids must be unique and align with feature columns")
        if not np.isfinite(features).all():
            raise ValueError("Probe features must be finite")
        if not set(np.unique(labels)).issubset({0, 1}):
            raise ValueError("Probe labels must be binary 0/1")
        owned_features = features.astype(np.float64, copy=True)
        owned_labels = labels.astype(np.int64, copy=True)
        owned_features.setflags(write=False)
        owned_labels.setflags(write=False)
        object.__setattr__(self, "features", owned_features)
        object.__setattr__(self, "labels", owned_labels)


@dataclass(frozen=True)
class LinearProbe:
    """Fitted standardization and logistic weights from development data only."""

    mean: np.ndarray
    scale: np.ndarray
    weights: np.ndarray
    bias: float
    l2: float
    fit_sample_ids: tuple[str, ...]
    feature_ids: tuple[str, ...]
    fit_split: str
    converged: bool
    iterations: int

    def __post_init__(self) -> None:
        for field_name in ("mean", "scale", "weights"):
            owned = np.asarray(getattr(self, field_name), dtype=np.float64).copy()
            owned.setflags(write=False)
            object.__setattr__(self, field_name, owned)

    def predict_scores(self, features: np.ndarray) -> np.ndarray:
        """Return probabilities using only statistics saved from the fit split."""
        values = np.asarray(features, dtype=np.float64)
        if values.ndim != 2 or values.shape[1] != self.weights.shape[0]:
            raise ValueError("Feature shape does not match fitted probe")
        if not np.isfinite(values).all():
            raise ValueError("Probe features must be finite")
        return expit(((values - self.mean) / self.scale) @ self.weights + self.bias)


@dataclass(frozen=True)
class ProbeMetrics:
    """Deterministic binary ranking metrics and counts."""

    auroc: float
    pr_auc: float
    accuracy_at_half: float
    positives: int
    negatives: int
    sample_count: int


def _validate_protocol(fit: ProbeData, evaluation: ProbeData, expected_evaluation_split: str) -> None:
    if fit.split != "development":
        raise PermissionError("Probe fitting is restricted to development data")
    if evaluation.split != expected_evaluation_split:
        raise PermissionError(f"Expected evaluation split {expected_evaluation_split!r}")
    if evaluation.split == "test":
        raise PermissionError("Test probe evaluation remains locked in this development implementation")
    overlap = set(fit.sample_ids) & set(evaluation.sample_ids)
    if overlap:
        raise ValueError(f"Fit/evaluation sample ids overlap: {sorted(overlap)}")
    if fit.features.shape[1] != evaluation.features.shape[1]:
        raise ValueError("Fit/evaluation feature dimensions differ")
    if fit.feature_ids != evaluation.feature_ids:
        raise ValueError("Fit/evaluation feature provenance differs")


def fit_linear_probe(data: ProbeData, *, l2: float = 1.0, max_iterations: int = 1000) -> LinearProbe:
    """Fit deterministic L2 logistic regression using development samples only."""
    if data.split != "development":
        raise PermissionError("Probe fitting is restricted to development data")
    if set(np.unique(data.labels)) != {0, 1}:
        raise ValueError("Fit data must contain both classes")
    if not isfinite(l2) or l2 < 0 or type(max_iterations) is not int or max_iterations < 1:
        raise ValueError("L2 must be finite/nonnegative and max_iterations positive")
    mean = data.features.mean(axis=0)
    scale = data.features.std(axis=0)
    scale[scale == 0] = 1.0
    x = (data.features - mean) / scale
    y = data.labels.astype(np.float64)

    def objective(parameters: np.ndarray) -> tuple[float, np.ndarray]:
        weights, bias = parameters[:-1], parameters[-1]
        logits = x @ weights + bias
        sample_count = len(y)
        loss = (np.logaddexp(0, logits).sum() - y @ logits) / sample_count + 0.5 * l2 * (weights @ weights)
        residual = expit(logits) - y
        gradient = np.concatenate((x.T @ residual / sample_count + l2 * weights,
                                   [residual.sum() / sample_count]))
        return float(loss), gradient

    optimized = minimize(objective, np.zeros(x.shape[1] + 1), jac=True, method="L-BFGS-B",
                         options={"maxiter": max_iterations, "ftol": 1e-12, "gtol": 1e-8})
    if not np.isfinite(optimized.x).all() or not isfinite(float(optimized.fun)):
        raise RuntimeError("Probe optimization produced non-finite values")
    if not optimized.success:
        raise RuntimeError(f"Probe optimization failed: {optimized.message}")
    return LinearProbe(mean, scale, optimized.x[:-1], float(optimized.x[-1]), l2,
                       data.sample_ids, data.feature_ids, data.split, True, int(optimized.nit))


def binary_probe_metrics(labels: Sequence[int], scores: Sequence[float]) -> ProbeMetrics:
    """Compute tie-aware AUROC and average precision without threshold tuning."""
    y = np.asarray(labels, dtype=np.int64)
    probability = np.asarray(scores, dtype=np.float64)
    if y.ndim != 1 or probability.ndim != 1 or len(y) != len(probability) or len(y) < 2:
        raise ValueError("Labels and scores must be aligned one-dimensional arrays")
    if set(np.unique(y)) != {0, 1}:
        raise ValueError("Evaluation metrics require both binary classes")
    if not np.isfinite(probability).all() or np.any((probability < 0) | (probability > 1)):
        raise ValueError("Scores must be finite probabilities")
    positives = int(y.sum())
    negatives = int(len(y) - positives)
    ranks = rankdata(probability, method="average")
    auroc = (ranks[y == 1].sum() - positives * (positives + 1) / 2) / (positives * negatives)
    order = np.argsort(-probability, kind="stable")
    ordered_labels = y[order]
    ordered_scores = probability[order]
    group_ends = np.flatnonzero(np.r_[ordered_scores[1:] != ordered_scores[:-1], True])
    cumulative_positives = np.cumsum(ordered_labels)[group_ends]
    retrieved = group_ends + 1
    precision = cumulative_positives / retrieved
    recall = cumulative_positives / positives
    average_precision = float(np.sum(np.diff(np.r_[0.0, recall]) * precision))
    accuracy = float(np.mean((probability >= 0.5).astype(np.int64) == y))
    return ProbeMetrics(float(auroc), average_precision, accuracy, positives, negatives, len(y))


def evaluate_probe(probe: LinearProbe, fit: ProbeData, evaluation: ProbeData, *,
                   expected_evaluation_split: str = "development") -> ProbeMetrics:
    """Evaluate a probe only after identity, split and feature leakage checks."""
    _validate_protocol(fit, evaluation, expected_evaluation_split)
    if (probe.fit_sample_ids != fit.sample_ids or probe.feature_ids != fit.feature_ids
            or probe.fit_split != fit.split):
        raise ValueError("Probe provenance does not match supplied fit data")
    return binary_probe_metrics(evaluation.labels, probe.predict_scores(evaluation.features))


def permutation_controls(fit: ProbeData, evaluation: ProbeData, *, seeds: Sequence[int],
                         l2: float = 1.0, expected_evaluation_split: str = "development") -> tuple[ProbeMetrics, ...]:
    """Fit seeded label-permutation controls without mutating caller-owned data."""
    _validate_protocol(fit, evaluation, expected_evaluation_split)
    if not seeds or any(type(seed) is not int for seed in seeds) or len(set(seeds)) != len(seeds):
        raise ValueError("Permutation seeds must be a nonempty unique integer sequence")
    results = []
    for seed in seeds:
        labels = np.random.default_rng(seed).permutation(fit.labels)
        permuted = ProbeData(fit.features, labels, fit.sample_ids, fit.feature_ids, fit.split)
        probe = fit_linear_probe(permuted, l2=l2)
        results.append(evaluate_probe(probe, permuted, evaluation,
                                      expected_evaluation_split=expected_evaluation_split))
    return tuple(results)
