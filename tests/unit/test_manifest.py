"""Tests for experiment reproducibility manifests."""

from pathlib import Path

from experiments.manifest import create_run_manifest, write_run_manifest


def test_manifest_contains_required_reproducibility_fields(tmp_path: Path) -> None:
    manifest = create_run_manifest(
        experiment_id="P0_test_20261011_manifest_0",
        run_id="manifest_test_0",
        model_id="fixture",
        model_revision="fixture-v1",
        tokenizer_revision="not-applicable",
        dataset_id="aether-fixtures",
        dataset_version="v0.1.0",
        dataset_split="fixture",
        subset_ids=["case_000"],
        seeds=[42],
        config_file=Path("configs/experiments/review_target.yaml"),
        raw_output_path=Path("results/raw/p1_review_target_results.csv"),
        dataset_files=[Path("data/attack_cases/MANIFEST.json")],
        artifact_paths=[Path("results/raw/p1_review_target_results.csv")],
        timing_seconds={"wall": 0.1},
    )
    required = {
        "run_id",
        "utc_timestamp",
        "git_commit",
        "uncommitted_diff",
        "dataset_manifest_hashes",
        "model_id",
        "model_revision",
        "tokenizer_revision",
        "prompt_versions",
        "random_seeds",
        "hardware",
        "python_env_hash",
        "command_line",
        "config_file",
        "raw_output_path",
        "dataset_id",
        "dataset_version",
        "dataset_split",
        "subset_ids",
        "artifact_paths",
        "timing_seconds",
    }
    assert required <= manifest.keys()
    assert manifest["python_version"].startswith("3.11.")
    assert len(manifest["python_env_hash"]) == 64

    destination = tmp_path / "manifest.json"
    write_run_manifest(manifest, destination)
    assert destination.exists()
    assert not destination.with_suffix(".json.tmp").exists()


def test_manifest_rejects_implicit_missing_metadata() -> None:
    common = {
        "experiment_id": "P0_test_20261011_invalid_0",
        "run_id": "invalid_0",
        "model_id": "fixture",
        "model_revision": "fixture-v1",
        "tokenizer_revision": "not_applicable",
        "dataset_id": "",
        "dataset_version": "unknown",
        "dataset_split": "fixture",
        "subset_ids": ["not_applicable"],
        "seeds": [42],
        "config_file": Path("configs/experiments/review_target.yaml"),
        "raw_output_path": Path("results/raw/p1_review_target_results.csv"),
    }
    try:
        create_run_manifest(**common)
    except ValueError as error:
        assert "dataset_id" in str(error)
    else:
        raise AssertionError("blank dataset identity was accepted")
