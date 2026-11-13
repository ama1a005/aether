"""Toy checkpoint verification for the Qwen SAE evaluation runner."""

import hashlib

import numpy as np
import torch

from causal.interventions.sae import SAEProvenance, write_sae_metadata
from experiments.phase1.qwen_sae_evaluation import evaluate


def test_sae_evaluation_retains_per_case_metrics(tmp_path) -> None:
    checkpoint = tmp_path / "sae"
    checkpoint.mkdir()
    weights = checkpoint / "weights.npz"
    np.savez(weights, encoder_weight=np.eye(2, dtype=np.float32), encoder_bias=np.zeros(2, dtype=np.float32),
             decoder_weight=np.eye(2, dtype=np.float32), decoder_bias=np.zeros(2, dtype=np.float32),
             mean=np.zeros(2, dtype=np.float32), scale=np.ones(2, dtype=np.float32))
    write_sae_metadata(checkpoint / "metadata.json", SAEProvenance(
        1, "toy", "model", "rev", "component", 2, 2, "relu", "none", 0.0,
        "training", 0, hashlib.sha256(weights.read_bytes()).hexdigest()))
    activations = tmp_path / "activations.pt"
    torch.save({"case": torch.ones(1, 2)}, activations)
    result = evaluate({"model_id": "model", "model_revision": "rev", "component_id": "component"}, checkpoint, activations)
    assert result["overall"] == "PASS" and result["case_count"] == 1
    assert result["rows"][0]["relative_reconstruction_error"] == 0
