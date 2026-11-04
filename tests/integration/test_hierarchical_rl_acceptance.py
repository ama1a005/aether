import json

from experiments.phase1.hierarchical_rl_smoke import ROOT, run


def test_hierarchical_rl_acceptance_is_multiseed_manifest_backed(tmp_path):
    destination = run(ROOT / "configs/experiments/hierarchical_rl_synthetic.yaml", tmp_path)
    payload = json.loads((destination / "results.json").read_text(encoding="utf-8"))
    manifest = json.loads((destination / "manifest.json").read_text(encoding="utf-8"))
    assert all(payload["checks"].values())
    assert set(payload["outcomes"]) == {"7", "9", "11"}
    assert payload["validation_executions"] == payload["test_executions"] == 0
    assert manifest["random_seeds"] == [7, 9, 11]
    assert manifest["dataset_split"] == "synthetic"
