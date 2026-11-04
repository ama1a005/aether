"""Pinned, portable linear SAE checkpoints for intervention experiments."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from math import isfinite
from pathlib import Path

import numpy as np
import torch


@dataclass(frozen=True)
class SAEProvenance:
    """Identity, normalization and acceptance metadata for one trained SAE."""
    schema_version: int
    sae_id: str
    model_id: str
    model_revision: str
    component_id: str
    input_dim: int
    latent_dim: int
    activation: str
    normalization: str
    max_relative_reconstruction_error: float
    training_dataset_hash: str
    training_seed: int
    weights_sha256: str

    def __post_init__(self) -> None:
        strings = (self.sae_id, self.model_id, self.model_revision, self.component_id,
                   self.training_dataset_hash, self.weights_sha256)
        if self.schema_version != 1 or any(not value.strip() for value in strings):
            raise ValueError("Complete SAE schema-v1 provenance is required")
        if self.input_dim < 1 or self.latent_dim < 1 or self.training_seed < 0:
            raise ValueError("SAE dimensions and seed are invalid")
        if self.activation not in {"relu", "identity"}:
            raise ValueError("Unsupported SAE activation")
        if self.normalization not in {"feature_standardization", "none"}:
            raise ValueError("Unsupported SAE normalization")
        threshold = self.max_relative_reconstruction_error
        if not isfinite(threshold) or threshold < 0:
            raise ValueError("SAE reconstruction threshold must be finite and nonnegative")
        if len(self.weights_sha256) != 64:
            raise ValueError("SAE weights SHA-256 is invalid")


class LinearSAE:
    """Inference-only SAE codec loaded from non-executable NPZ weights."""

    def __init__(self, provenance: SAEProvenance, tensors: dict[str, torch.Tensor]) -> None:
        self.provenance = provenance
        self._tensors = tensors

    def _aligned(self, name: str, like: torch.Tensor) -> torch.Tensor:
        return self._tensors[name].to(device=like.device, dtype=like.dtype)

    def _normalize(self, activation: torch.Tensor) -> torch.Tensor:
        if activation.shape[-1] != self.provenance.input_dim:
            raise ValueError("Activation hidden dimension does not match SAE")
        if not activation.is_floating_point() or not torch.isfinite(activation).all():
            raise ValueError("SAE inputs must be finite floating tensors")
        if self.provenance.normalization == "none":
            return activation
        return ((activation - self._aligned("mean", activation)) /
                self._aligned("scale", activation))

    def encode(self, activation: torch.Tensor) -> torch.Tensor:
        """Normalize and encode model activations into pinned latent features."""
        normalized = self._normalize(activation)
        features = normalized @ self._aligned("encoder_weight", activation).T
        features = features + self._aligned("encoder_bias", activation)
        return torch.relu(features) if self.provenance.activation == "relu" else features

    def decode(self, features: torch.Tensor) -> torch.Tensor:
        """Decode features and invert the checkpoint's declared normalization."""
        if features.shape[-1] != self.provenance.latent_dim:
            raise ValueError("Feature dimension does not match SAE")
        if not features.is_floating_point() or not torch.isfinite(features).all():
            raise ValueError("SAE features must be finite floating tensors")
        decoded = features @ self._aligned("decoder_weight", features).T
        decoded = decoded + self._aligned("decoder_bias", features)
        if self.provenance.normalization == "feature_standardization":
            decoded = decoded * self._aligned("scale", features) + self._aligned("mean", features)
        return decoded

    def relative_reconstruction_error(self, activation: torch.Tensor) -> float:
        """Return RMSE divided by input RMS with a stable zero-input denominator."""
        reconstructed = self.decode(self.encode(activation))
        error = torch.sqrt(torch.mean(torch.square(reconstructed - activation)))
        scale = torch.sqrt(torch.mean(torch.square(activation))).clamp_min(1e-12)
        value = float((error / scale).item())
        if not isfinite(value):
            raise RuntimeError("SAE reconstruction metric is nonfinite")
        return value

    def validate_reconstruction(self, activation: torch.Tensor) -> float:
        """Fail if reconstruction exceeds the checkpoint's predeclared threshold."""
        value = self.relative_reconstruction_error(activation)
        if value > self.provenance.max_relative_reconstruction_error:
            raise ValueError(
                f"SAE reconstruction error {value:.6g} exceeds threshold "
                f"{self.provenance.max_relative_reconstruction_error:.6g}")
        return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_sae_checkpoint(directory: Path, *, expected_model_id: str,
                        expected_model_revision: str,
                        expected_component_id: str) -> LinearSAE:
    """Load and validate metadata plus non-executable NPZ tensors."""
    metadata_path = directory / "metadata.json"
    weights_path = directory / "weights.npz"
    if not metadata_path.is_file() or not weights_path.is_file():
        raise FileNotFoundError("SAE metadata.json and weights.npz are required")
    raw = json.loads(metadata_path.read_text(encoding="utf-8"))
    provenance = SAEProvenance(**raw)
    expected = (expected_model_id, expected_model_revision, expected_component_id)
    observed = (provenance.model_id, provenance.model_revision, provenance.component_id)
    if observed != expected:
        raise ValueError("SAE model/component provenance mismatch")
    if _sha256(weights_path) != provenance.weights_sha256:
        raise ValueError("SAE weights hash mismatch")
    required = {"encoder_weight", "encoder_bias", "decoder_weight", "decoder_bias",
                "mean", "scale"}
    with np.load(weights_path, allow_pickle=False) as archive:
        if set(archive.files) != required:
            raise ValueError("SAE checkpoint tensor set is invalid")
        tensors = {name: torch.from_numpy(np.asarray(archive[name], dtype=np.float32).copy())
                   for name in required}
    shapes = {
        "encoder_weight": (provenance.latent_dim, provenance.input_dim),
        "encoder_bias": (provenance.latent_dim,),
        "decoder_weight": (provenance.input_dim, provenance.latent_dim),
        "decoder_bias": (provenance.input_dim,), "mean": (provenance.input_dim,),
        "scale": (provenance.input_dim,),
    }
    if any(tuple(tensors[name].shape) != shape for name, shape in shapes.items()):
        raise ValueError("SAE checkpoint tensor shape mismatch")
    if any(not torch.isfinite(tensor).all() for tensor in tensors.values()):
        raise ValueError("SAE checkpoint contains nonfinite tensors")
    if provenance.normalization == "feature_standardization" and torch.any(tensors["scale"] <= 0):
        raise ValueError("SAE normalization scales must be positive")
    return LinearSAE(provenance, tensors)


def write_sae_metadata(path: Path, provenance: SAEProvenance) -> None:
    """Write canonical metadata for a separately trained checkpoint."""
    path.write_text(json.dumps(asdict(provenance), indent=2, sort_keys=True), encoding="utf-8")
