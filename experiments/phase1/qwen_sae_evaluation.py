"""Evaluate a pinned trained SAE on retained Qwen activations without fallbacks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import torch
import yaml

from causal.interventions.sae import load_sae_checkpoint
from experiments.external_bundle import runtime_metadata, sha256_file, verify_protocol_approval, write_bundle_manifest


ROOT = Path(__file__).resolve().parents[2]


def evaluate(config: dict[str, Any], checkpoint: Path, activations: Path) -> dict[str, Any]:
    """Verify provenance and compute declared reconstruction/sparsity metrics."""
    codec = load_sae_checkpoint(
        checkpoint, expected_model_id=str(config["model_id"]),
        expected_model_revision=str(config["model_revision"]),
        expected_component_id=str(config["component_id"]),
    )
    payload = torch.load(activations, map_location="cpu", weights_only=True)
    if not isinstance(payload, dict) or not payload:
        raise ValueError("Qwen SAE activation artifact must be a nonempty tensor mapping")
    rows = []
    for case_id, tensor in sorted(payload.items()):
        if not isinstance(case_id, str) or not isinstance(tensor, torch.Tensor):
            raise TypeError("SAE activation entries require string IDs and tensors")
        error = codec.validate_reconstruction(tensor)
        features = codec.encode(tensor)
        rows.append({"case_id": case_id, "relative_reconstruction_error": error,
                     "active_fraction": float((features != 0).float().mean().item()),
                     "activation_shape": list(tensor.shape)})
    maximum = max(row["relative_reconstruction_error"] for row in rows)
    return {"overall": "PASS", "model_id": config["model_id"],
            "model_revision": config["model_revision"], "component_id": config["component_id"],
            "sae_id": codec.provenance.sae_id, "case_count": len(rows),
            "maximum_relative_reconstruction_error": maximum, "rows": rows,
            "validation_executions": 0, "test_executions": 0,
            "claim_boundary": "Reconstruction/sparsity evidence only; no causal SAE-feature claim."}


def run(config_path: Path, approval_path: Path, output: Path) -> Path:
    """Run only a reviewed, development-only trained-SAE protocol."""
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    verify_protocol_approval(config_path, approval_path)
    if config.get("status") != "awaiting_human_checkpoint_and_protocol_review":
        raise ValueError("unexpected trained-SAE proposal status")
    if config.get("split") != "development" or config.get("validation_executions") != 0 or config.get("test_executions") != 0:
        raise PermissionError("trained-SAE protocol attempts protected-split access")
    checkpoint = Path(config["checkpoint_path"])
    activations = Path(config["activation_path"])
    result = evaluate(config, checkpoint, activations)
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    destination = output / "summary.json"
    destination.write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
    metadata = runtime_metadata(
        repository=ROOT, experiment_id="P0_sae_qwen15b_development", run_id=output.name,
        dataset_manifest_hashes={str(activations): sha256_file(activations),
                                 str(checkpoint / "metadata.json"): sha256_file(checkpoint / "metadata.json")},
        model_id=str(config["model_id"]), model_revision=str(config["model_revision"]),
        tokenizer_revision=str(config["model_revision"]), seeds=[0], config_file=config_path,
        evidence_kind="qwen_sae")
    write_bundle_manifest(output, metadata)
    return destination


def main() -> None:
    """Execute the reviewed trained-SAE evaluation."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--approval", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    print(run(arguments.config, arguments.approval, arguments.output))


if __name__ == "__main__":
    main()
