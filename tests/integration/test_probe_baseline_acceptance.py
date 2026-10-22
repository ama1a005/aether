"""Integration acceptance for the synthetic, model-free probe baseline."""

import json
from pathlib import Path

from experiments.phase1.probe_baseline_smoke import ROOT, run


def test_probe_acceptance_writes_passing_results_and_manifest(tmp_path: Path):
    destination = run(ROOT / "configs/experiments/probe_baseline_synthetic.yaml", tmp_path)
    results = json.loads((destination / "results.json").read_text(encoding="utf-8"))
    manifest = json.loads((destination / "manifest.json").read_text(encoding="utf-8"))
    assert all(results["checks"].values())
    assert results["validation_executions"] == results["test_executions"] == 0
    assert results["claim_limit"].startswith("Synthetic software acceptance only")
    assert manifest["run_id"] == results["run_id"]
    assert manifest["dataset_split"] == "synthetic_development"
