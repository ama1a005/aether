import hashlib
import json

import pytest
import yaml

from evaluation.final_report import generate_report
from evaluation.phase1_statistics import OutcomeRecord


def write_run(root, dirty=False):
    root.mkdir()
    records = [OutcomeRecord("a", 0, "full", "family", True, True, True, True,
                             faithfulness=.9, benign_damage=.1, forward_passes=4),
               OutcomeRecord("a", 0, "receiver", "family", True, True, False, True,
                             faithfulness=.5, benign_damage=.05, forward_passes=2)]
    outcome = root / "outcomes.json"
    outcome.write_text(json.dumps({"run_id": "run", "records": [row.__dict__ for row in records]}))
    digest = hashlib.sha256(outcome.read_bytes()).hexdigest()
    manifest = {"experiment_id": "exp", "run_id": "run", "git_commit": "abc",
        "uncommitted_diff": dirty, "dataset_manifest_hashes": {"dataset": "hash"},
        "model_id": "model", "model_revision": "rev", "tokenizer_revision": "rev",
        "random_seeds": [0], "python_env_hash": "env", "config_hash": "config",
        "dataset_split": "development", "artifact_paths": {str(outcome): digest}}
    (root / "manifest.json").write_text(json.dumps(manifest))


def test_report_requires_verified_complete_runs(tmp_path):
    run = tmp_path / "run"
    write_run(run)
    config = {"schema_version": 1, "split": "development", "require_clean_git": True,
              "required_experiment_ids": ["exp"], "bootstrap_seed": 0,
              "bootstrap_samples": 100, "paired_method_comparisons": [["full", "receiver"]]}
    path = tmp_path / "report.yaml"
    path.write_text(yaml.safe_dump(config))
    report_path = generate_report(path, [run], tmp_path / "output")
    report = json.loads(report_path.read_text())
    assert report["statistics"]["full"]["asr"] == 1
    assert (tmp_path / "output" / "method_summary.csv").is_file()
    assert (tmp_path / "output" / "asr_by_method.png").is_file()

    outcome = run / "outcomes.json"
    outcome.write_text(outcome.read_text() + " ")
    with pytest.raises(ValueError, match="hash"):
        generate_report(path, [run], tmp_path / "tampered")


def test_report_rejects_dirty_runs(tmp_path):
    run = tmp_path / "run"
    write_run(run, dirty=True)
    config = {"schema_version": 1, "split": "development", "require_clean_git": True,
              "required_experiment_ids": ["exp"], "bootstrap_seed": 0,
              "bootstrap_samples": 10, "paired_method_comparisons": []}
    path = tmp_path / "report.yaml"
    path.write_text(yaml.safe_dump(config))
    with pytest.raises(ValueError, match="dirty"):
        generate_report(path, [run], tmp_path / "output")
