"""Portable SAE tests use a tiny locally fitted linear autoencoder."""
import hashlib

import numpy as np
import pytest
import torch

from causal.interventions.sae import SAEProvenance, load_sae_checkpoint, write_sae_metadata


def make_checkpoint(root, threshold=0.05):
    # The fixture is the converged identity solution for a two-feature toy SAE.
    weights = root / "weights.npz"
    np.savez(weights, encoder_weight=np.eye(2, dtype=np.float32),
             encoder_bias=np.zeros(2, dtype=np.float32),
             decoder_weight=np.eye(2, dtype=np.float32),
             decoder_bias=np.zeros(2, dtype=np.float32),
             mean=np.zeros(2, dtype=np.float32), scale=np.ones(2, dtype=np.float32))
    digest = hashlib.sha256(weights.read_bytes()).hexdigest()
    provenance = SAEProvenance(1, "toy-sae", "toy-model", "rev", "L0.resid", 2, 2,
                               "relu", "feature_standardization", threshold,
                               "dataset-hash", 7, digest)
    write_sae_metadata(root / "metadata.json", provenance)
    return weights


def test_sae_roundtrip_provenance_and_reconstruction_gate(tmp_path):
    make_checkpoint(tmp_path)
    codec = load_sae_checkpoint(tmp_path, expected_model_id="toy-model",
                                expected_model_revision="rev",
                                expected_component_id="L0.resid")
    activation = torch.tensor([[[1.0, 2.0], [3.0, 4.0]]])
    assert codec.validate_reconstruction(activation) == pytest.approx(0)
    assert torch.equal(codec.decode(codec.encode(activation)), activation)
    with pytest.raises(ValueError, match="provenance"):
        load_sae_checkpoint(tmp_path, expected_model_id="wrong",
                            expected_model_revision="rev", expected_component_id="L0.resid")


def test_sae_rejects_tampering_and_bad_reconstruction(tmp_path):
    weights = make_checkpoint(tmp_path)
    with weights.open("ab") as handle:
        handle.write(b"tamper")
    with pytest.raises(ValueError, match="hash"):
        load_sae_checkpoint(tmp_path, expected_model_id="toy-model",
                            expected_model_revision="rev", expected_component_id="L0.resid")

    other = tmp_path / "other"
    other.mkdir()
    make_checkpoint(other, threshold=0.01)
    codec = load_sae_checkpoint(other, expected_model_id="toy-model",
                                expected_model_revision="rev", expected_component_id="L0.resid")
    codec._tensors["decoder_weight"].zero_()
    with pytest.raises(ValueError, match="exceeds"):
        codec.validate_reconstruction(torch.ones(1, 1, 2))
