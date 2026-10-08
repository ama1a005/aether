import os
import torch
from pathlib import Path

class ActivationCache:
    def __init__(self, cache_dir: str = 'results/raw/activation_cache'):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def save(self, run_id: str, component_id: str, tensor: torch.Tensor):
        run_dir = self.cache_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        torch.save(tensor, run_dir / f"{component_id}.pt")

    def load(self, run_id: str, component_id: str) -> torch.Tensor:
        path = self.cache_dir / run_id / f"{component_id}.pt"
        if not path.exists():
            raise FileNotFoundError(f"Activation not found: {path}")
        return torch.load(path)

    def clear(self, run_id: str):
        run_dir = self.cache_dir / run_id
        if run_dir.exists():
            for f in run_dir.glob("*.pt"):
                f.unlink()
            run_dir.rmdir()
