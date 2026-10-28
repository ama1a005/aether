"""Manifest acceptance for the mandatory Agent C pipeline."""

import json
from pathlib import Path
from experiments.phase1.three_agent_smoke import ROOT, run


def test_three_agent_acceptance_writes_manifest(tmp_path: Path):
    destination = run(ROOT / "configs/experiments/three_agent_synthetic.yaml", tmp_path)
    result = json.loads((destination / "results.json").read_text(encoding="utf-8"))
    manifest = json.loads((destination / "manifest.json").read_text(encoding="utf-8"))
    assert all(result["checks"].values())
    assert manifest["run_id"] == result["run_id"]
    assert result["validation_executions"] == result["test_executions"] == 0
