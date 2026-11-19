"""Model-independent tests for the approved dual-T4 SAE package."""

import json
from pathlib import Path

import pytest
import torch

from experiments.phase1.qwen_sae_training import (
    TorchSAE,
    NoEligibleSeed,
    authorization,
    finalize_rejected_seeds,
    select_corpus_tokens,
    select_seed,
    train_seed,
)
from scripts.generate_qwen_sae_kaggle_notebook import generate
from scripts.ingest_qwen_sae_bundle import ingest
from scripts.verify_qwen_sae_bundle import verify


class _Tokenizer:
    eos_token_id = 99

    def encode(self, text: str, add_special_tokens: bool) -> list[int]:
        assert add_special_tokens is False
        return [ord(character) for character in text]


def test_exact_approved_chain_is_authorized() -> None:
    base, amendment = authorization()
    assert base["minimum_training_rows"] == 10000
    assert amendment["training_corpus"]["training_token_count"] == 57344
    assert amendment["training_corpus"]["dataset_revision"] == (
        "b08601e04326c79dfdd32d625aee71d232d685c3"
    )


def test_corpus_selection_is_ordered_skips_empty_and_truncates_exactly() -> None:
    observed = select_corpus_tokens([" ", "ab", "cde"], _Tokenizer(), selected_token_count=6)
    assert observed.tolist() == [97, 98, 99, 99, 100, 101]


def test_corpus_selection_rejects_insufficient_source() -> None:
    with pytest.raises(ValueError, match="did not provide"):
        select_corpus_tokens(["a"], _Tokenizer(), selected_token_count=4)


def test_frozen_torch_sae_shapes() -> None:
    model = TorchSAE(8, 12)
    reconstruction, features = model(torch.randn(3, 8))
    assert reconstruction.shape == (3, 8)
    assert features.shape == (3, 12)
    assert torch.all(features >= 0)


def test_seed_selection_requires_all_seeds_and_uses_error_then_seed(tmp_path) -> None:
    for seed, error in ((11, 0.2), (22, 0.1), (33, 0.1)):
        root = tmp_path / f"seed-{seed}"
        root.mkdir()
        (root / "seed_summary.json").write_text(json.dumps({
            "seed": seed,
            "scientific_outcome": "SAE_SEED_ELIGIBLE",
            "best_selection": {"relative_reconstruction_error": error},
            "validation_executions": 0,
            "test_executions": 0,
        }), encoding="utf-8")
    assert select_seed(tmp_path).name == "seed-22"


def test_all_seed_rejection_is_retained_without_audit(tmp_path) -> None:
    seeds = tmp_path / "seeds"
    for seed in (11, 22, 33):
        root = seeds / f"seed-{seed}"
        root.mkdir(parents=True)
        (root / "seed_summary.json").write_text(json.dumps({
            "seed": seed, "scientific_outcome": "SAE_SEED_REJECTED_NO_ELIGIBLE_CHECKPOINT",
            "best_selection": None, "epochs_completed": 100,
            "validation_executions": 0, "test_executions": 0,
        }), encoding="utf-8")
    with pytest.raises(NoEligibleSeed):
        select_seed(seeds)
    destination = finalize_rejected_seeds(seeds, tmp_path / "final")
    summary = json.loads(destination.read_text(encoding="utf-8"))
    assert summary["overall"] == "FAIL"
    assert summary["scientific_outcome"] == "SAE_REJECTED_NO_ELIGIBLE_SEED"


def test_training_refuses_incomplete_capture_before_allocating_model(tmp_path) -> None:
    with pytest.raises(ValueError, match="expected 256 corpus blocks"):
        train_seed(tmp_path / "blocks", tmp_path / "seed-11", seed=11, device="cpu")


def test_generated_notebook_is_multigpu_resumable_and_syntax_valid(tmp_path) -> None:
    destination = tmp_path / "sae.ipynb"
    commit = "a" * 40
    generate(commit, destination)
    notebook = json.loads(destination.read_text(encoding="utf-8"))
    sources = ["".join(cell["source"]) for cell in notebook["cells"]
               if cell["cell_type"] == "code"]
    for index, source in enumerate(sources):
        compile(source, f"cell-{index}", "exec")
    joined = "\n".join(sources)
    assert commit in joined
    assert "for gpu in (0,1)" in joined and "f'cuda:{gpu}'" in joined
    assert "run_with_sync" in joined and "AETHER_HF_REPO" in joined
    assert "api.upload_folder" in joined
    assert "stop.wait(60)" in joined
    assert "sync_errors.append(error)" in joined
    assert "api.upload_file(path_or_fileobj=str(path)" not in joined
    assert "subprocess.run([str(PY),'-c',token_code" in joined
    assert "subprocess.check_output([str(PY),'-c',selection_code" in joined
    assert "hf_hub_download" in joined
    assert "wikitext-2-raw-v1/train-00000-of-00001.parquet" in joined
    assert "b08601e04326c79dfdd32d625aee71d232d685c3" in joined
    assert "e83889baabc497075506f91975be5fac0d45c5290b6b20582c8cd1e853d0c9f7" in joined
    assert "observed_data_hash==DATA_SHA256" in joined
    assert joined.index("hf_hub_download(repo_id=DATA_ID") < joined.index(
        "snapshot_download(MODEL_ID"
    )
    assert "allow_patterns='wikitext-2-raw-v1/*'" not in joined
    assert "{{" not in joined and "}}" not in joined
    assert "REMOTE_SOURCE_PREFIX" in joined and "sae-v1-2" in joined
    assert "v1.3 requires the retained v1.2 epoch-10 files" in joined
    assert "training_checkpoint.pt" in joined and "training_history.jsonl" in joined
    assert "finalize-rejected-seeds" in joined


def test_bundle_verifier_rejects_missing_inventory(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="archive_contents"):
        verify(tmp_path)


def test_atomic_ingester_copies_verified_bundle_and_exposes_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, destination = tmp_path / "source", tmp_path / "destination"
    (source / "final").mkdir(parents=True)
    (source / "final/summary.json").write_text(
        json.dumps({"overall": "FAIL", "scientific_outcome": "SAE_REJECTED"}),
        encoding="utf-8",
    )
    monkeypatch.setattr("scripts.ingest_qwen_sae_bundle.verify", lambda _root: {
        "bundle_valid": True, "scientific_outcome": "SAE_REJECTED"
    })
    receipt = ingest(source, destination)
    assert receipt["verification"]["bundle_valid"] is True
    assert json.loads((destination / "summary.json").read_text())["overall"] == "FAIL"
    with pytest.raises(FileExistsError):
        ingest(source, destination)
