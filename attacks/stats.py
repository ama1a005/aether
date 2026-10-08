import numpy as np
from typing import Tuple, List
import math

def bootstrap_ci(successes: int, n: int, n_bootstrap: int = 1000, confidence: float = 0.95, seed: int = 42) -> Tuple[float, float]:
    rng = np.random.RandomState(seed)
    if n == 0:
        return (0.0, 0.0)
    data = np.array([1] * successes + [0] * (n - successes))
    boot_means = []
    for _ in range(n_bootstrap):
        sample = rng.choice(data, size=n, replace=True)
        boot_means.append(np.mean(sample))
    
    alpha = 1.0 - confidence
    lower = float(np.percentile(boot_means, alpha / 2 * 100))
    upper = float(np.percentile(boot_means, (1 - alpha / 2) * 100))
    return lower, upper

def paired_mcnemar(y_clean: List[bool], y_attacked: List[bool]) -> Tuple[float, float]:
    b = sum(1 for c, a in zip(y_clean, y_attacked) if c and not a)
    c = sum(1 for c, a in zip(y_clean, y_attacked) if not c and a)
    
    if b + c == 0:
        return 0.0, 1.0
        
    statistic = ((abs(b - c) - 1) ** 2) / (b + c)
    z = np.sqrt(statistic)
    p_value = 2 * (1.0 - 0.5 * (1.0 + math.erf(z / math.sqrt(2))))
    
    return float(statistic), float(p_value)

def effect_size_odds_ratio(asr_a: float, asr_b: float) -> float:
    def odds(p: float) -> float:
        p = max(1e-6, min(1 - 1e-6, p))
        return p / (1 - p)
    
    return odds(asr_a) / odds(asr_b)
