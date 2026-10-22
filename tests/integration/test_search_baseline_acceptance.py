"""Execute the model-free baseline command and verify its artifact provenance."""

import json
from pathlib import Path

from experiments.manifest import sha256_file
from experiments.phase1.search_baseline_smoke import ROOT, run


def test_search_acceptance_saves_raw_queries_and_manifest(tmp_path: Path) -> None:
    directory = run(ROOT / "configs/experiments/search_baselines_synthetic.yaml", tmp_path)
    result = json.loads((directory / "results.json").read_text(encoding="utf-8"))
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    assert all(result["checks"].values())
    assert result["validation_executions"] == result["test_executions"] == 0
    assert manifest["run_id"] == result["run_id"]
    assert manifest["dataset_split"] == "synthetic"
    assert manifest["random_seeds"] == [0]
    for path, digest in manifest["artifact_paths"].items():
        assert sha256_file(Path(path)) == digest
    for method in result["results"].values():
        assert method["queries"] == len(method["records"]) <= 64
        assert method["forward_passes"] == sum(row["evaluation"]["forward_passes"] for row in method["records"])
        assert all(row["evaluation"]["raw_outputs"] for row in method["records"])
    assert (directory / "results.json").exists()
