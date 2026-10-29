from discovery.random_baseline.sampler import RandomCircuitSampler
from discovery.greedy.pruner import GreedyCausalPruner
import torch
from causal.metrics.faithfulness import compute_faithfulness
from discovery.budgeted import Candidate, matched_random_masks

def test_random_sampler_size():
    candidates = [{'id': str(i), 'region': 'sender'} for i in range(10)]
    sampler = RandomCircuitSampler(candidates)
    res = sampler.sample(3, 42)
    assert len(res) == 3

def test_random_sampler_deterministic():
    candidates = [{'id': str(i), 'region': 'sender'} for i in range(10)]
    sampler = RandomCircuitSampler(candidates)
    res1 = sampler.sample(3, 42)
    res2 = sampler.sample(3, 42)
    assert res1 == res2

def test_random_sampler_region_balance():
    candidates = [Candidate(f"{region}{i}", region)
                  for region in ("sender", "message", "receiver") for i in range(3)]
    masks = matched_random_masks(candidates, ["sender0", "message0", "receiver0"],
                                  samples=12, seed=42)
    assert len(masks) == 12
    for mask in masks:
        assert all(sum(node.startswith(region) for node in mask) == 1
                   for region in ("sender", "message", "receiver"))

def _prune(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "results/raw").mkdir(parents=True)
    def model(x):
        return (x * torch.tensor([2., 0., 0.])).sum()
    def ablate(model, x, components):
        patched = x.clone()
        for component in components:
            patched[int(component)] = 0
        return model(patched), {}
    pruner = GreedyCausalPruner(model, None, ablate, compute_faithfulness,
                                ["0", "1", "2"], 0.9)
    retained, history = pruner.prune([torch.ones(3)], [torch.zeros(3)])
    return pruner, retained, history

def test_greedy_pruner_reduces_size(tmp_path, monkeypatch):
    _, retained, _ = _prune(tmp_path, monkeypatch)
    assert retained == ["0"]

def test_greedy_pruner_faithfulness_maintained(tmp_path, monkeypatch):
    pruner, _, history = _prune(tmp_path, monkeypatch)
    assert all(faithfulness >= 0.9 for _, _, faithfulness in history)
    assert pruner.benign_damage == 0
