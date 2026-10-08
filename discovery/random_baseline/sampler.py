import random
from typing import List, Dict, Any

class RandomCircuitSampler:
    def __init__(self, candidates: List[Dict[str, Any]]):
        self.candidates = candidates
        
    def sample(self, k: int, seed: int) -> List[Dict[str, Any]]:
        if k >= len(self.candidates):
            return list(self.candidates)
            
        # simple random sample to preserve ratios approx
        rng = random.Random(seed)
        return rng.sample(self.candidates, k)
        
    def sample_many(self, k: int, n_samples: int, seed: int) -> List[List[Dict[str, Any]]]:
        rng = random.Random(seed)
        return [self.sample(k, rng.randint(0, 2**32-1)) for _ in range(n_samples)]
