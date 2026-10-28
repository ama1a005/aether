"""Manifest-backed synthetic acceptance for advanced intervention operators."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
from time import perf_counter
from uuid import uuid4

import torch
from torch import nn
import yaml

from causal.interventions.advanced import InterventionTarget, execute_path_patch
from experiments.manifest import create_run_manifest, write_run_manifest

ROOT = Path(__file__).resolve().parents[2]


class _IdentityCodec:
    def encode(self, activation: torch.Tensor) -> torch.Tensor:
        return activation

    def decode(self, features: torch.Tensor) -> torch.Tensor:
        return features


class _ToyPath(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.sender = nn.Identity()
        self.receiver = nn.Identity()
        self.readout = nn.Linear(4, 1, bias=False)
        with torch.no_grad():
            self.readout.weight.fill_(1.0)

    def forward(self, values: torch.Tensor) -> torch.Tensor:
        return self.readout(self.receiver(self.sender(values))[:, -1])


def run(config_path: Path, output_root: Path | None = None) -> Path:
    """Execute all advanced operators on a deterministic toy path."""
    config_path = config_path.resolve()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if config["evidence_class"] != "synthetic_acceptance_only" or config["split"] != "synthetic":
        raise ValueError("Advanced intervention smoke accepts synthetic configurations only")
    started = perf_counter()
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(config["seed"])
        model = _ToyPath().eval()
    attacked = torch.zeros(1, 2, 4)
    clean = torch.ones_like(attacked)
    baseline = model(attacked)
    targets = (
        InterventionTarget("sender.residual", "sender", (0,), "synthetic-clean"),
        InterventionTarget("receiver.head0", "receiver", (1,), "synthetic-clean",
                           operator="head_output_patch", head_indices=(0,), num_heads=2),
    )
    patched, records = execute_path_patch(model, attacked, targets,
                                          {target.component_id: clean for target in targets})
    sae_target = InterventionTarget("receiver.sae", "receiver", (1,), "synthetic-clean",
                                    operator="sae_feature_patch", feature_indices=(2, 3))
    sae_patched, sae_records = execute_path_patch(
        model, attacked, [sae_target], {"receiver.sae": clean}, {"receiver.sae": _IdentityCodec()})
    checks = {
        "path_patch_changes_output": patched.item() > baseline.item(),
        "sae_patch_changes_selected_features": sae_patched.item() > baseline.item(),
        "all_operator_records_present": {record.operator for record in (*records, *sae_records)}
            == {"residual_patch", "head_output_patch", "sae_feature_patch"},
        "hooks_removed": not model.sender._forward_hooks and not model.receiver._forward_hooks,
    }
    run_id = f"{config['experiment_id']}_{uuid4().hex}"
    destination = (output_root or ROOT / config["output_root"]) / run_id
    destination.mkdir(parents=True, exist_ok=False)
    output = destination / "results.json"
    payload = {"run_id": run_id, "utc_timestamp": datetime.now(timezone.utc).isoformat(),
               "evidence_class": config["evidence_class"], "checks": checks,
               "raw_outputs": {"baseline": baseline.tolist(), "path_patched": patched.tolist(),
                               "sae_patched": sae_patched.tolist()},
               "interventions": [asdict(record) for record in (*records, *sae_records)],
               "validation_executions": 0, "test_executions": 0,
               "claim_limit": "Synthetic operator acceptance only; no model or causal localization claim."}
    output.write_text(json.dumps(payload, indent=2, allow_nan=False), encoding="utf-8")
    manifest = create_run_manifest(
        experiment_id=config["experiment_id"], run_id=run_id, model_id="toy_path",
        model_revision="v1", tokenizer_revision="not_applicable",
        dataset_id="synthetic_advanced_operator_acceptance", dataset_version="v1",
        dataset_split="synthetic", subset_ids=["two_token_four_hidden"], seeds=[config["seed"]],
        config_file=config_path, raw_output_path=output, dataset_files=[Path(__file__).resolve()],
        intervention_config={"operators": sorted({record.operator for record in (*records, *sae_records)}),
                             "source_run": "synthetic-clean"},
        artifact_paths=[output, ROOT / "causal/interventions/advanced.py"],
        timing_seconds={"execution": perf_counter() - started}, repository=ROOT)
    write_run_manifest(manifest, destination / "manifest.json")
    if not all(checks.values()):
        raise RuntimeError(f"Advanced intervention acceptance failed; evidence saved in {destination}")
    return destination


def main() -> None:
    """Run configured synthetic acceptance and print its artifact directory."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path,
                        default=ROOT / "configs/experiments/advanced_interventions_synthetic.yaml")
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args()
    print(f"ADVANCED INTERVENTION ACCEPTANCE PASSED: {run(args.config, args.output_root)}")


if __name__ == "__main__":
    main()
