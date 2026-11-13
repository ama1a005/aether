"""Scientific statistics: Wilson score confidence intervals and cluster-adjusted uncertainty."""

from __future__ import annotations

import math
from typing import Any, Sequence


def calculate_binomial_confidence_interval(
    successes: int,
    total: int,
    confidence: float = 0.95,
) -> tuple[float, float]:
    """Calculate the Wilson score confidence interval for a binomial proportion.

    Robust for small samples and extreme proportions (near 0 or 1), avoiding the
    degenerate zero-width intervals of the Wald normal approximation.
    """
    if total <= 0:
        return 0.0, 0.0
    if successes < 0 or successes > total:
        raise ValueError(f"Successes {successes} must be between 0 and total {total}")

    # Standard normal critical value for two-sided confidence
    # For 0.95, z ~ 1.95996; for 0.99, z ~ 2.57583; for 0.90, z ~ 1.64485
    if abs(confidence - 0.95) < 1e-4:
        z = 1.959963984540054
    elif abs(confidence - 0.99) < 1e-4:
        z = 2.5758293035489004
    elif abs(confidence - 0.90) < 1e-4:
        z = 1.6448536269514722
    else:
        # Approximate using rational formula for norm.ppf((1 + confidence) / 2)
        # using a simple approximation
        alpha = 1.0 - confidence
        p = 1.0 - alpha / 2.0
        t = math.sqrt(-2.0 * math.log(1.0 - p))
        c0, c1, c2 = 2.515517, 0.802853, 0.010328
        d1, d2, d3 = 1.432788, 0.189269, 0.001308
        z = t - (c0 + c1 * t + c2 * t * t) / (1.0 + d1 * t + d2 * t * t + d3 * t * t * t)

    p_hat = successes / total
    z2 = z * z
    denom = 1.0 + z2 / total
    center = (p_hat + z2 / (2.0 * total)) / denom
    margin = (z / denom) * math.sqrt((p_hat * (1.0 - p_hat) / total) + (z2 / (4.0 * total * total)))

    lower = 0.0 if successes == 0 else max(0.0, center - margin)
    upper = 1.0 if successes == total else min(1.0, center + margin)
    return lower, upper


def calculate_cluster_confidence_interval(
    cases: Sequence[dict[str, Any]],
    cluster_key: str,
    success_key: str = "is_attack_success",
    confidence: float = 0.95,
) -> dict[str, Any]:
    """Calculate cluster-adjusted proportion and uncertainty across grouped units.

    Avoids treating repeated observations within the same server or scenario
    as independent samples.
    """
    if not cases:
        return {"proportion": 0.0, "ci_lower": 0.0, "ci_upper": 0.0, "n_clusters": 0}

    clusters: dict[str, list[bool]] = {}
    for c in cases:
        ck = str(c.get(cluster_key, "default"))
        val = bool(c.get(success_key, False))
        clusters.setdefault(ck, []).append(val)

    m = len(clusters)
    if m == 0:
        return {"proportion": 0.0, "ci_lower": 0.0, "ci_upper": 0.0, "n_clusters": 0}

    # Cluster-level proportions
    cluster_means = [sum(vals) / len(vals) for vals in clusters.values() if vals]
    if not cluster_means:
        return {"proportion": 0.0, "ci_lower": 0.0, "ci_upper": 0.0, "n_clusters": 0}

    mean_prop = sum(cluster_means) / len(cluster_means)
    if len(cluster_means) > 1:
        var = sum((cm - mean_prop) ** 2 for cm in cluster_means) / (len(cluster_means) - 1)
        se = math.sqrt(var / len(cluster_means))
    else:
        se = 0.0

    z = 1.95996 if abs(confidence - 0.95) < 1e-4 else 1.96
    lower = max(0.0, mean_prop - z * se)
    upper = min(1.0, mean_prop + z * se)

    return {
        "cluster_key": cluster_key,
        "n_clusters": m,
        "cluster_adjusted_mean": mean_prop,
        "standard_error": se,
        "ci_lower": lower,
        "ci_upper": upper,
        "confidence": confidence,
    }
