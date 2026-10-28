"""Integration acceptance for model-free PPO search comparison."""

import json
from pathlib import Path

from experiments.phase1.rl_search_smoke import ROOT, run


def test_rl_acceptance_writes_comparison_ablation_and_manifest(tmp_path: Path):
    destination = run(ROOT / "configs/experiments/rl_search_synthetic.yaml", tmp_path)
    result = json.loads((destination / "results.json").read_text(encoding="utf-8"))
    manifest = json.loads((destination / "manifest.json").read_text(encoding="utf-8"))
    assert all(result["checks"].values())
    assert set(result["results"]) == {"greedy", "beam", "ppo", "matched_random"}
    assert set(result["reward_ablations"]) == {"no_size", "no_cost", "no_stop_bonus"}
    assert len(result["ppo_training_trace"]) == 128
    assert all(len(trace) == 128 for trace in result["reward_ablation_training_traces"].values())
    assert result["validation_executions"] == result["test_executions"] == 0
    assert manifest["run_id"] == result["run_id"]
    assert manifest["dataset_split"] == "synthetic"
