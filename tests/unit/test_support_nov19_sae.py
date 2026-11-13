"""Unit tests for SUPPORT-03: SAE evaluation runner."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import numpy as np
import pytest
import torch

from experiments.supporting_nov19.sae.runner import (
    EXTERNAL_TENSOR_ARCHIVE_SHA256,
    QCI2_CANDIDATES,
    validate_sae_config,
)
from experiments.supporting_nov19.red_team.adapter import (
    QUALIFIED_MODEL_ID,
    QUALIFIED_MODEL_REVISION,
)


def _valid_sae_config(tmp_path: Path | None = None) -> dict:
    return {
        "schema_version": "aether.supporting-nov19.sae.v1",
        "model_id": QUALIFIED_MODEL_ID,
        "model_revision": QUALIFIED_MODEL_REVISION,
        "tokenizer_revision": QUALIFIED_MODEL_REVISION,
        "dtype": "float32",
        "device": "cpu",
        "component_id": "receiver.module.L22.attention_output",
        "seed": 0,
        "output_dir": str(tmp_path or "/tmp/sae_out"),
        "source_commit": "00846b020b685dfa3ab89bce2c5227d2810c9d1e",
        "external_tensor_archive_sha256": EXTERNAL_TENSOR_ARCHIVE_SHA256,
    }


class TestValidateSaeConfig:
    def test_valid_config_passes(self):
        errors = validate_sae_config(_valid_sae_config())
        assert errors == []

    def test_wrong_model_id_rejected(self):
        config = _valid_sae_config()
        config["model_id"] = "meta/llama-3"
        errors = validate_sae_config(config)
        assert any("model_id" in e for e in errors)

    def test_missing_component_id_rejected(self):
        config = _valid_sae_config()
        del config["component_id"]
        errors = validate_sae_config(config)
        assert any("component_id" in e for e in errors)


class TestQCI2Candidates:
    def test_four_candidates_declared(self):
        assert len(QCI2_CANDIDATES) == 4

    def test_candidate_ids_are_strings(self):
        assert all(isinstance(c, str) and c.strip() for c in QCI2_CANDIDATES)


class TestExternalArchiveNote:
    def test_sha256_is_declared(self):
        assert len(EXTERNAL_TENSOR_ARCHIVE_SHA256) == 64
        assert all(c in "0123456789abcdef" for c in EXTERNAL_TENSOR_ARCHIVE_SHA256)


class TestLinearSAEContract:
    """Test SAE checkpoint loading contract (no real model, uses synthetic tensors)."""

    def _make_checkpoint(self, tmp_path: Path, input_dim: int = 8,
                         latent_dim: int = 16) -> Path:
        """Create a minimal valid SAE checkpoint for testing."""
        from causal.interventions.sae import SAEProvenance, write_sae_metadata
        import hashlib

        weights = {
            "encoder_weight": np.random.randn(latent_dim, input_dim).astype(np.float32),
            "encoder_bias": np.random.randn(latent_dim).astype(np.float32),
            "decoder_weight": np.random.randn(input_dim, latent_dim).astype(np.float32),
            "decoder_bias": np.random.randn(input_dim).astype(np.float32),
            "mean": np.zeros(input_dim, dtype=np.float32),
            "scale": np.ones(input_dim, dtype=np.float32),
        }
        weights_path = tmp_path / "weights.npz"
        np.savez(weights_path, **weights)

        sha256 = hashlib.sha256()
        with weights_path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                sha256.update(chunk)
        weights_hash = sha256.hexdigest()

        provenance = SAEProvenance(
            schema_version=1,
            sae_id="test_sae_001",
            model_id=QUALIFIED_MODEL_ID,
            model_revision=QUALIFIED_MODEL_REVISION,
            component_id="receiver.module.L22.attention_output",
            input_dim=input_dim,
            latent_dim=latent_dim,
            activation="relu",
            normalization="none",
            max_relative_reconstruction_error=10.0,
            training_dataset_hash="a" * 64,
            training_seed=0,
            weights_sha256=weights_hash,
        )
        write_sae_metadata(tmp_path / "metadata.json", provenance)
        return tmp_path

    def test_load_valid_checkpoint(self, tmp_path):
        from causal.interventions.sae import load_sae_checkpoint
        chk = self._make_checkpoint(tmp_path)
        sae = load_sae_checkpoint(
            chk,
            expected_model_id=QUALIFIED_MODEL_ID,
            expected_model_revision=QUALIFIED_MODEL_REVISION,
            expected_component_id="receiver.module.L22.attention_output",
        )
        assert sae.provenance.sae_id == "test_sae_001"

    def test_reconstruction_roundtrip(self, tmp_path):
        from causal.interventions.sae import load_sae_checkpoint
        chk = self._make_checkpoint(tmp_path, input_dim=8, latent_dim=16)
        sae = load_sae_checkpoint(
            chk,
            expected_model_id=QUALIFIED_MODEL_ID,
            expected_model_revision=QUALIFIED_MODEL_REVISION,
            expected_component_id="receiver.module.L22.attention_output",
        )
        activation = torch.randn(1, 8)
        err = sae.relative_reconstruction_error(activation)
        assert isinstance(err, float)
        assert err >= 0

    def test_wrong_model_id_rejected(self, tmp_path):
        from causal.interventions.sae import load_sae_checkpoint
        chk = self._make_checkpoint(tmp_path)
        with pytest.raises(ValueError, match="provenance mismatch"):
            load_sae_checkpoint(
                chk,
                expected_model_id="wrong/model",
                expected_model_revision=QUALIFIED_MODEL_REVISION,
                expected_component_id="receiver.module.L22.attention_output",
            )
