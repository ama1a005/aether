"""SUPPORT-03: Standalone SAE training package.

Provides a reproducible sparse-autoencoder trainer matched to the AETHER
activation schema. The trainer:
  - Accepts hash-verified input data (from the external tensor archive)
  - Trains an L2 reconstruction + L1 sparse penalty SAE
  - Saves metadata-rich checkpoints compatible with `causal.interventions.sae`
  - Computes baseline comparisons (mean-vector / zero reconstruction)

NOTE: This module does NOT edit any frozen core file. It produces checkpoints
that are consumed by the existing `load_sae_checkpoint()` API.

Usage:
    python -m experiments.supporting_nov19.sae.trainer \\
        --data-dir <path/to/verified/activations> \\
        --component-id sender.module.L22.attention_output \\
        --output-dir results/phase1/sae/qwen15b/trained_checkpoint \\
        --epochs 50 --latent-dim 512 --sparsity-weight 1e-3
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from experiments.supporting_nov19.red_team.adapter import (
    QUALIFIED_MODEL_ID,
    QUALIFIED_MODEL_REVISION,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCHEMA_VERSION = 1  # Must match causal/interventions/sae.py SAEProvenance
DEFAULT_LATENT_DIM = 512
DEFAULT_LR = 1e-3
DEFAULT_SPARSITY_WEIGHT = 1e-3
DEFAULT_EPOCHS = 50
DEFAULT_BATCH_SIZE = 64
DEFAULT_ACTIVATION = "relu"
DEFAULT_NORMALIZATION = "feature_standardization"


# ---------------------------------------------------------------------------
# Hash verification
# ---------------------------------------------------------------------------

def verify_file_sha256(path: Path, expected_sha256: str | None = None) -> str:
    """Compute SHA256 of a file and optionally verify against expected hash.

    Returns the computed hash. Raises ValueError on mismatch.
    """
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    computed = h.hexdigest()
    if expected_sha256 is not None and computed != expected_sha256:
        raise ValueError(
            f"SHA256 mismatch for {path.name}: "
            f"expected {expected_sha256[:16]}..., got {computed[:16]}..."
        )
    return computed


# ---------------------------------------------------------------------------
# Baseline computations (no torch dependency for interface)
# ---------------------------------------------------------------------------

def compute_mean_baseline(activations: Any) -> float:
    """Mean-vector reconstruction baseline: RMSE of (X - mean(X))."""
    import numpy as np  # noqa: PLC0415
    if not isinstance(activations, np.ndarray):
        activations = np.array(activations, dtype=np.float32)
    mean_vec = activations.mean(axis=0, keepdims=True)
    residual = activations - mean_vec
    rmse = float(np.sqrt(np.mean(residual ** 2)))
    rms_input = float(np.sqrt(np.mean(activations ** 2)))
    return rmse / max(rms_input, 1e-12)


def compute_zero_baseline(activations: Any) -> float:
    """Zero-reconstruction baseline: RMSE of X itself (reconstruct = 0)."""
    import numpy as np  # noqa: PLC0415
    if not isinstance(activations, np.ndarray):
        activations = np.array(activations, dtype=np.float32)
    return 1.0  # RMSE/RMS = 1.0 by definition when reconstruction is zero


# ---------------------------------------------------------------------------
# SAE Trainer (numpy-only for portability; torch optional)
# ---------------------------------------------------------------------------

class SAETrainer:
    """Reproducible sparse autoencoder trainer.

    Architecture: Linear encoder -> activation -> Linear decoder
    Loss: L2_reconstruction + sparsity_weight * L1_latent
    """

    def __init__(
        self,
        input_dim: int,
        latent_dim: int = DEFAULT_LATENT_DIM,
        lr: float = DEFAULT_LR,
        sparsity_weight: float = DEFAULT_SPARSITY_WEIGHT,
        activation: str = DEFAULT_ACTIVATION,
        normalization: str = DEFAULT_NORMALIZATION,
        seed: int = 42,
    ) -> None:
        import numpy as np  # noqa: PLC0415
        self.input_dim = input_dim
        self.latent_dim = latent_dim
        self.lr = lr
        self.sparsity_weight = sparsity_weight
        self.activation = activation
        self.normalization = normalization
        self.seed = seed
        self.rng = np.random.RandomState(seed)

        # Xavier initialization
        scale = np.sqrt(2.0 / (input_dim + latent_dim))
        self.encoder_weight = self.rng.randn(input_dim, latent_dim).astype(np.float32) * scale
        self.encoder_bias = np.zeros(latent_dim, dtype=np.float32)
        self.decoder_weight = self.rng.randn(latent_dim, input_dim).astype(np.float32) * scale
        self.decoder_bias = np.zeros(input_dim, dtype=np.float32)

        # Normalization stats (computed from data)
        self.mean = np.zeros(input_dim, dtype=np.float32)
        self.scale = np.ones(input_dim, dtype=np.float32)

        self.training_history: list[dict[str, Any]] = []

    def _activate(self, z: Any) -> Any:
        """Apply activation function to latent codes."""
        import numpy as np  # noqa: PLC0415
        if self.activation == "relu":
            return np.maximum(z, 0)
        return z  # identity

    def _activate_grad(self, z: Any) -> Any:
        """Gradient of activation function."""
        import numpy as np  # noqa: PLC0415
        if self.activation == "relu":
            return (z > 0).astype(np.float32)
        return np.ones_like(z)

    def fit_normalization(self, data: Any) -> None:
        """Compute mean and scale from training data."""
        import numpy as np  # noqa: PLC0415
        if self.normalization == "feature_standardization":
            self.mean = data.mean(axis=0).astype(np.float32)
            self.scale = data.std(axis=0).astype(np.float32)
            self.scale = np.maximum(self.scale, 1e-8)  # prevent division by zero
        else:
            self.mean = np.zeros(self.input_dim, dtype=np.float32)
            self.scale = np.ones(self.input_dim, dtype=np.float32)

    def normalize(self, data: Any) -> Any:
        """Apply learned normalization."""
        return (data - self.mean) / self.scale

    def forward(self, x_norm: Any) -> tuple[Any, Any, Any]:
        """Forward pass: returns (reconstruction, latent_pre_act, latent_post_act)."""
        z_pre = x_norm @ self.encoder_weight + self.encoder_bias
        z = self._activate(z_pre)
        x_hat = z @ self.decoder_weight + self.decoder_bias
        return x_hat, z_pre, z

    def train_epoch(self, data: Any, batch_size: int = DEFAULT_BATCH_SIZE) -> dict[str, float]:
        """Run one training epoch with mini-batch SGD."""
        import numpy as np  # noqa: PLC0415
        n = len(data)
        indices = self.rng.permutation(n)
        total_recon = 0.0
        total_sparse = 0.0
        n_batches = 0

        for start in range(0, n, batch_size):
            batch_idx = indices[start:start + batch_size]
            x = data[batch_idx]
            x_norm = self.normalize(x)

            # Forward
            x_hat, z_pre, z = self.forward(x_norm)

            # Losses
            recon_loss = np.mean((x_hat - x_norm) ** 2)
            sparse_loss = np.mean(np.abs(z))
            total_recon += recon_loss
            total_sparse += sparse_loss

            # Backward (manual gradient)
            bs = len(batch_idx)
            d_x_hat = 2.0 * (x_hat - x_norm) / bs

            # Decoder gradients
            d_decoder_weight = z.T @ d_x_hat / bs
            d_decoder_bias = d_x_hat.mean(axis=0)

            # Latent gradients
            d_z = d_x_hat @ self.decoder_weight.T
            d_z += self.sparsity_weight * np.sign(z) / bs  # L1 gradient

            # Through activation
            d_z_pre = d_z * self._activate_grad(z_pre)

            # Encoder gradients
            d_encoder_weight = x_norm.T @ d_z_pre / bs
            d_encoder_bias = d_z_pre.mean(axis=0)

            # SGD update
            self.encoder_weight -= self.lr * d_encoder_weight
            self.encoder_bias -= self.lr * d_encoder_bias
            self.decoder_weight -= self.lr * d_decoder_weight
            self.decoder_bias -= self.lr * d_decoder_bias

            n_batches += 1

        metrics = {
            "recon_loss": total_recon / max(n_batches, 1),
            "sparse_loss": total_sparse / max(n_batches, 1),
            "total_loss": (total_recon + self.sparsity_weight * total_sparse) / max(n_batches, 1),
        }
        self.training_history.append(metrics)
        return metrics

    def train(
        self,
        data: Any,
        epochs: int = DEFAULT_EPOCHS,
        batch_size: int = DEFAULT_BATCH_SIZE,
        verbose: bool = True,
    ) -> list[dict[str, float]]:
        """Full training loop."""
        self.fit_normalization(data)
        history = []
        for epoch in range(epochs):
            metrics = self.train_epoch(data, batch_size)
            history.append(metrics)
            if verbose and (epoch % 10 == 0 or epoch == epochs - 1):
                print(
                    f"  Epoch {epoch+1:4d}/{epochs}: "
                    f"recon={metrics['recon_loss']:.6f}  "
                    f"sparse={metrics['sparse_loss']:.6f}  "
                    f"total={metrics['total_loss']:.6f}",
                    flush=True,
                )
        return history

    def evaluate_reconstruction(self, data: Any) -> float:
        """Compute relative reconstruction error on held-out data."""
        import numpy as np  # noqa: PLC0415
        x_norm = self.normalize(data)
        x_hat, _, _ = self.forward(x_norm)
        rmse = float(np.sqrt(np.mean((x_hat - x_norm) ** 2)))
        rms_input = float(np.sqrt(np.mean(x_norm ** 2)))
        return rmse / max(rms_input, 1e-12)

    def save_checkpoint(
        self,
        output_dir: Path,
        component_id: str,
        model_id: str = QUALIFIED_MODEL_ID,
        model_revision: str = QUALIFIED_MODEL_REVISION,
        data_sha256: str = "",
    ) -> Path:
        """Save checkpoint in format compatible with causal.interventions.sae."""
        import numpy as np  # noqa: PLC0415
        output_dir.mkdir(parents=True, exist_ok=True)

        sae_id = f"sae_{uuid.uuid4().hex[:12]}"

        # Metadata (matches SAEProvenance schema)
        metadata = {
            "schema_version": SCHEMA_VERSION,
            "sae_id": sae_id,
            "model_id": model_id,
            "model_revision": model_revision,
            "component_id": component_id,
            "input_dim": self.input_dim,
            "latent_dim": self.latent_dim,
            "activation": self.activation,
            "normalization": self.normalization,
            "max_relative_reconstruction_error": 0.10,
            "training_config": {
                "lr": self.lr,
                "sparsity_weight": self.sparsity_weight,
                "seed": self.seed,
                "epochs": len(self.training_history),
                "data_sha256": data_sha256,
            },
            "training_history": self.training_history[-5:],  # Last 5 epochs
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        meta_path = output_dir / "metadata.json"
        meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

        # Weights
        weights_path = output_dir / "weights.npz"
        np.savez(
            weights_path,
            encoder_weight=self.encoder_weight,
            encoder_bias=self.encoder_bias,
            decoder_weight=self.decoder_weight,
            decoder_bias=self.decoder_bias,
            mean=self.mean,
            scale=self.scale,
        )

        print(f"\nCheckpoint saved: {output_dir}", flush=True)
        print(f"  SAE ID: {sae_id}", flush=True)
        print(f"  Component: {component_id}", flush=True)
        print(f"  Dims: {self.input_dim} -> {self.latent_dim}", flush=True)
        return output_dir


# ---------------------------------------------------------------------------
# Feature ablation / patching operators
# ---------------------------------------------------------------------------

def ablate_features(
    activations: Any,
    sae_weights: dict[str, Any],
    feature_indices: list[int],
    method: str = "zero",
) -> Any:
    """Ablate specific SAE features and reconstruct.

    Methods:
        - "zero": Set selected latent features to zero
        - "mean": Set selected latent features to their training mean

    This is the intervention operator for causal probing of SAE features.
    """
    import numpy as np  # noqa: PLC0415
    enc_w = sae_weights["encoder_weight"]
    enc_b = sae_weights["encoder_bias"]
    dec_w = sae_weights["decoder_weight"]
    dec_b = sae_weights["decoder_bias"]
    mean = sae_weights.get("mean", np.zeros(activations.shape[-1]))
    scale = sae_weights.get("scale", np.ones(activations.shape[-1]))

    # Normalize
    x_norm = (activations - mean) / np.maximum(scale, 1e-12)

    # Encode
    z = x_norm @ enc_w + enc_b
    z = np.maximum(z, 0)  # ReLU

    # Ablate
    if method == "zero":
        z[:, feature_indices] = 0.0
    elif method == "mean":
        z[:, feature_indices] = z[:, feature_indices].mean()
    else:
        raise ValueError(f"Unknown ablation method: {method}")

    # Decode and denormalize
    x_hat = z @ dec_w + dec_b
    return x_hat * scale + mean


def patch_features(
    source_activations: Any,
    target_activations: Any,
    sae_weights: dict[str, Any],
    feature_indices: list[int],
) -> Any:
    """Activation-patch specific SAE features from source into target.

    Encodes both, copies selected features from source to target, decodes.
    This is the patching intervention for causal analysis.
    """
    import numpy as np  # noqa: PLC0415
    enc_w = sae_weights["encoder_weight"]
    enc_b = sae_weights["encoder_bias"]
    dec_w = sae_weights["decoder_weight"]
    dec_b = sae_weights["decoder_bias"]
    mean = sae_weights.get("mean", np.zeros(source_activations.shape[-1]))
    scale = sae_weights.get("scale", np.ones(source_activations.shape[-1]))

    # Normalize
    src_norm = (source_activations - mean) / np.maximum(scale, 1e-12)
    tgt_norm = (target_activations - mean) / np.maximum(scale, 1e-12)

    # Encode
    z_src = np.maximum(src_norm @ enc_w + enc_b, 0)
    z_tgt = np.maximum(tgt_norm @ enc_w + enc_b, 0)

    # Patch: copy selected features from source to target
    z_patched = z_tgt.copy()
    z_patched[:, feature_indices] = z_src[:, feature_indices]

    # Decode and denormalize
    x_hat = z_patched @ dec_w + dec_b
    return x_hat * scale + mean


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="SUPPORT-03: Train a sparse autoencoder on verified activations.",
    )
    parser.add_argument("--data-dir", type=Path, required=True,
                        help="Directory containing activation .npy files")
    parser.add_argument("--component-id", type=str, required=True,
                        help="Component ID (e.g. sender.module.L22.attention_output)")
    parser.add_argument("--output-dir", type=Path, required=True,
                        help="Where to save the trained checkpoint")
    parser.add_argument("--epochs", type=int, default=DEFAULT_EPOCHS)
    parser.add_argument("--latent-dim", type=int, default=DEFAULT_LATENT_DIM)
    parser.add_argument("--sparsity-weight", type=float, default=DEFAULT_SPARSITY_WEIGHT)
    parser.add_argument("--lr", type=float, default=DEFAULT_LR)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--data-sha256", type=str, default="",
                        help="Expected SHA256 of the input data archive for verification")
    args = parser.parse_args()

    import numpy as np  # noqa: PLC0415

    # Load and verify data
    data_path = args.data_dir / f"{args.component_id.replace('.', '_')}.npy"
    if not data_path.is_file():
        # Try glob
        npy_files = list(args.data_dir.glob("*.npy"))
        if not npy_files:
            print(f"ERROR: No .npy files found in {args.data_dir}", file=sys.stderr)
            print(
                "The 4.87 GB tensor archive must be downloaded and extracted. "
                "See docs/supporting_nov19/SAE_RUNBOOK.md for instructions.",
                file=sys.stderr,
            )
            return 1
        data_path = npy_files[0]
        print(f"Using {data_path.name} (no component-specific file found)")

    if args.data_sha256:
        print(f"Verifying SHA256 of {data_path.name}...")
        verify_file_sha256(data_path, args.data_sha256)
        print("  Hash verified OK")

    data = np.load(str(data_path))
    print(f"Loaded activation data: shape={data.shape}, dtype={data.dtype}")

    if data.ndim != 2:
        print(f"ERROR: Expected 2D array (samples x features), got {data.ndim}D", file=sys.stderr)
        return 1

    input_dim = data.shape[1]

    # Compute baselines
    mean_baseline = compute_mean_baseline(data)
    zero_baseline = compute_zero_baseline(data)
    print(f"\nBaseline reconstruction errors:")
    print(f"  Zero:  {zero_baseline:.6f}")
    print(f"  Mean:  {mean_baseline:.6f}")

    # Train SAE
    trainer = SAETrainer(
        input_dim=input_dim,
        latent_dim=args.latent_dim,
        lr=args.lr,
        sparsity_weight=args.sparsity_weight,
        seed=args.seed,
    )
    print(f"\nTraining SAE: {input_dim} -> {args.latent_dim} (ReLU, L1={args.sparsity_weight})")
    trainer.train(data, epochs=args.epochs, batch_size=args.batch_size)

    # Evaluate
    final_error = trainer.evaluate_reconstruction(data)
    print(f"\nFinal relative reconstruction error: {final_error:.6f}")
    print(f"  vs mean baseline: {mean_baseline:.6f}")
    print(f"  vs zero baseline: {zero_baseline:.6f}")

    if final_error < mean_baseline:
        print("  SAE outperforms mean-vector baseline")
    else:
        print("  WARNING: SAE does NOT outperform mean-vector baseline")

    # Save
    data_hash = verify_file_sha256(data_path) if args.data_sha256 else ""
    trainer.save_checkpoint(
        output_dir=args.output_dir,
        component_id=args.component_id,
        data_sha256=data_hash or args.data_sha256,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
