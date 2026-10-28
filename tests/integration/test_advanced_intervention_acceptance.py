"""Integration acceptance for advanced intervention operators."""

import json
from pathlib import Path

from experiments.phase1.advanced_intervention_smoke import ROOT, run


def test_advanced_intervention_acceptance_writes_manifest(tmp_path: Path):
    destination = run(ROOT / "configs/experiments/advanced_interventions_synthetic.yaml", tmp_path)
    result = json.loads((destination / "results.json").read_text(encoding="utf-8"))
    manifest = json.loads((destination / "manifest.json").read_text(encoding="utf-8"))
    assert all(result["checks"].values())
    assert result["validation_executions"] == result["test_executions"] == 0
    assert manifest["run_id"] == result["run_id"]
    assert manifest["dataset_split"] == "synthetic"
