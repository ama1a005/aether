"""Fail-fast verification for the isolated AETHER demo GPU environment."""

from __future__ import annotations

import json
import platform
import sys

import torch


def main() -> None:
    """Print machine-readable diagnostics and fail unless CUDA execution works."""
    payload = {
        "python": sys.version,
        "executable": sys.executable,
        "platform": platform.platform(),
        "torch": torch.__version__,
        "torch_cuda": torch.version.cuda,
        "cuda_available": torch.cuda.is_available(),
        "device_count": torch.cuda.device_count(),
    }
    if torch.cuda.is_available():
        payload["device_name"] = torch.cuda.get_device_name(0)
        probe = torch.tensor([1.0], device="cuda") * 2
        payload["cuda_probe"] = probe.item()
    print(json.dumps(payload, indent=2))
    if not torch.cuda.is_available():
        raise SystemExit("CUDA verification failed: torch.cuda.is_available() is false")


if __name__ == "__main__":
    main()
