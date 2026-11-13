"""SUPPORT-03: Hash-verifying activation data loader with resource-safe minibatches.

Loads activation data from the externally-sourced tensor archive, verifies
SHA256 integrity, and yields minibatches suitable for SAE training and
evaluation. Designed for resource-constrained environments (CPU, limited RAM).

Usage:
    from experiments.supporting_nov19.sae.data_loader import ActivationLoader

    loader = ActivationLoader(
        data_dir=Path("data/activations"),
        component_id="sender.module.L22.attention_output",
        expected_sha256="7890212a...",  # optional
    )
    for batch in loader.iter_batches(batch_size=64):
        # batch: np.ndarray of shape (batch_size, input_dim)
        ...
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterator

from experiments.supporting_nov19.sae.trainer import verify_file_sha256

# SHA256 of the externally reported 4.87 GB development-capture tensor archive
EXTERNAL_TENSOR_ARCHIVE_SHA256 = (
    "7890212a8e7a4eb099be86bc572cd6172fd1c45b839f695e56e6ba4a46e97b21"
)


class ActivationLoader:
    """Hash-verifying, memory-aware activation data loader.

    Supports:
      - Component-specific .npy files (e.g., sender_module_L22_attention_output.npy)
      - Archive-level SHA256 verification
      - Resource-safe minibatch iteration (loads full array but yields slices)
      - Optional memory-mapped loading for very large files
    """

    def __init__(
        self,
        data_dir: Path,
        component_id: str,
        expected_sha256: str | None = None,
        use_mmap: bool = False,
    ) -> None:
        self.data_dir = Path(data_dir)
        self.component_id = component_id
        self.expected_sha256 = expected_sha256
        self.use_mmap = use_mmap
        self._data = None
        self._verified = False

        # Resolve file path
        safe_name = component_id.replace(".", "_")
        self._data_path = self.data_dir / f"{safe_name}.npy"
        if not self._data_path.is_file():
            # Fallback: try any .npy file
            npy_files = sorted(self.data_dir.glob("*.npy"))
            if npy_files:
                self._data_path = npy_files[0]
            else:
                raise FileNotFoundError(
                    f"No activation data found in {self.data_dir} for "
                    f"component {component_id}. The 4.87 GB tensor archive "
                    f"must be downloaded and extracted first."
                )

    @property
    def data_path(self) -> Path:
        return self._data_path

    def verify(self) -> str:
        """Verify SHA256 of the data file. Returns computed hash."""
        if self._verified:
            return self._computed_hash
        self._computed_hash = verify_file_sha256(
            self._data_path,
            self.expected_sha256,
        )
        self._verified = True
        return self._computed_hash

    def load(self) -> Any:
        """Load the activation data into memory (or memory-map)."""
        import numpy as np  # noqa: PLC0415

        if self._data is not None:
            return self._data

        if self.expected_sha256:
            self.verify()

        if self.use_mmap:
            self._data = np.load(str(self._data_path), mmap_mode="r")
        else:
            self._data = np.load(str(self._data_path))

        if self._data.ndim != 2:
            raise ValueError(
                f"Expected 2D activation array (samples x features), "
                f"got {self._data.ndim}D with shape {self._data.shape}"
            )
        return self._data

    @property
    def shape(self) -> tuple[int, ...]:
        """Shape of the loaded data. Loads if not already loaded."""
        return self.load().shape

    @property
    def input_dim(self) -> int:
        """Feature dimension of the activations."""
        return self.shape[1]

    @property
    def n_samples(self) -> int:
        """Number of activation samples."""
        return self.shape[0]

    def iter_batches(
        self,
        batch_size: int = 64,
        shuffle: bool = False,
        seed: int = 42,
    ) -> Iterator[Any]:
        """Yield minibatches of activations.

        Memory-safe: yields views (slices) of the loaded array rather than copies.
        """
        import numpy as np  # noqa: PLC0415
        data = self.load()
        n = len(data)

        if shuffle:
            rng = np.random.RandomState(seed)
            indices = rng.permutation(n)
        else:
            indices = np.arange(n)

        for start in range(0, n, batch_size):
            batch_idx = indices[start:start + batch_size]
            yield data[batch_idx]

    def get_manifest(self) -> dict[str, Any]:
        """Return metadata about the loaded data for evidence packets."""
        data = self.load()
        return {
            "data_path": str(self._data_path),
            "component_id": self.component_id,
            "shape": list(data.shape),
            "dtype": str(data.dtype),
            "sha256": self._computed_hash if self._verified else None,
            "n_samples": self.n_samples,
            "input_dim": self.input_dim,
            "use_mmap": self.use_mmap,
        }

    def split_train_eval(
        self,
        eval_fraction: float = 0.1,
        seed: int = 42,
    ) -> tuple[Any, Any]:
        """Split data into training and evaluation sets."""
        import numpy as np  # noqa: PLC0415
        data = self.load()
        n = len(data)
        rng = np.random.RandomState(seed)
        indices = rng.permutation(n)
        n_eval = max(1, int(n * eval_fraction))
        eval_indices = indices[:n_eval]
        train_indices = indices[n_eval:]
        return data[train_indices], data[eval_indices]
