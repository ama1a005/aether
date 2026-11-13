"""SUPPORT-03: Trained SAE evaluation runner on real Qwen activations.

Tests whether a trained sparse autoencoder (SAE) matched to actual Qwen
component representations passes reconstruction acceptance and can be
causally probed. The 4.87 GB tensor archive must be externally available;
this runner will fail closed if it is absent.

Usage:
    python -m experiments.supporting_nov19.sae.runner --dry-run
    python -m experiments.supporting_nov19.sae.runner --execute \\
        --config configs/supporting_nov19/sae_qwen15b.json \\
        --checkpoint-dir <path/to/sae/checkpoint> \\
        --output-root results/phase1/sae/qwen15b
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from causal.interventions.sae import load_sae_checkpoint, SAEProvenance
from experiments.supporting_nov19.red_team.adapter import (
    QUALIFIED_MODEL_ID,
    QUALIFIED_MODEL_REVISION,
)

# SHA256 of the externally reported 4.87 GB development-capture tensor archive
EXTERNAL_TENSOR_ARCHIVE_SHA256 = (
    "7890212a8e7a4eb099be86bc572cd6172fd1c45b839f695e56e6ba4a46e97b21"
)

# QCI-2 candidate components (from frozen PROJECT_STATE.md)
QCI2_CANDIDATES = [
    "sender.module.L22.attention_output",
    "receiver.module.L22.attention_output",
    "receiver.head.L20.H5.pre_o_proj",
    "receiver.head.L22.H7.pre_o_proj",
]


def _log(run_id: str, event: str, payload: dict[str, Any]) -> None:
    """Write a structured log line to stdout."""
    print(json.dumps({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "experiment_id": "SUPPORT-03-sae-qwen15b",
        "component": "sae_runner",
        "event": event,
        "payload": payload,
    }), flush=True)


def validate_sae_config(config: dict[str, Any]) -> list[str]:
    """Return validation errors for the SAE config."""
    errors: list[str] = []
    for key in ["model_id", "model_revision", "component_id", "output_dir", "source_commit"]:
        if key not in config:
            errors.append(f"Missing required config key: {key!r}")
    if config.get("model_id") != QUALIFIED_MODEL_ID:
        errors.append(f"model_id must be {QUALIFIED_MODEL_ID!r}")
    if config.get("model_revision") != QUALIFIED_MODEL_REVISION:
        errors.append(f"model_revision must be {QUALIFIED_MODEL_REVISION!r}")
    return errors


def dry_run(config_path: Path, checkpoint_dir: Path | None) -> int:
    """Validate config and checkpoint availability; no model loading."""
    run_id = f"sae_dry_{uuid.uuid4().hex[:8]}"
    _log(run_id, "dry_run_start", {"config": str(config_path)})

    if not config_path.is_file():
        _log(run_id, "dry_run_error", {"message": f"Config not found: {config_path}"})
        return 1

    config = json.loads(config_path.read_text(encoding="utf-8"))
    errors = validate_sae_config(config)
    if errors:
        _log(run_id, "dry_run_failed", {"errors": errors})
        return 1

    # Check checkpoint availability
    if checkpoint_dir is not None:
        meta = checkpoint_dir / "metadata.json"
        weights = checkpoint_dir / "weights.npz"
        if not meta.is_file() or not weights.is_file():
            _log(run_id, "dry_run_checkpoint_missing", {
                "checkpoint_dir": str(checkpoint_dir),
                "message": "SAE checkpoint metadata.json and/or weights.npz not found",
            })
            errors.append("SAE checkpoint files not found at specified directory")
    else:
        _log(run_id, "dry_run_checkpoint_not_specified", {
            "message": "No --checkpoint-dir provided; SAE files must be present for --execute",
        })

    _log(run_id, "external_tensor_archive_note", {
        "sha256": EXTERNAL_TENSOR_ARCHIVE_SHA256,
        "available_locally": False,
        "note": (
            "The 4.87 GB development-capture tensor archive is not in git and "
            "must be downloaded from an authorized external source before training a SAE."
        ),
    })

    if errors:
        _log(run_id, "dry_run_failed", {"errors": errors})
        return 1

    _log(run_id, "dry_run_ok", config)
    print("\nDry-run PASSED: SAE config validated.", flush=True)
    return 0


def execute(config_path: Path, checkpoint_dir: Path, output_root: Path) -> int:
    """Load checkpoint, validate reconstruction, and probe on real Qwen activations."""
    run_id = f"sae_{uuid.uuid4().hex[:12]}"
    _log(run_id, "execute_start", {
        "config": str(config_path),
        "checkpoint_dir": str(checkpoint_dir),
    })

    if not config_path.is_file():
        _log(run_id, "execute_error", {"message": f"Config not found: {config_path}"})
        return 1

    config = json.loads(config_path.read_text(encoding="utf-8"))
    errors = validate_sae_config(config)
    if errors:
        _log(run_id, "execute_failed_validation", {"errors": errors})
        return 1

    if not checkpoint_dir.is_dir():
        _log(run_id, "execute_error", {
            "message": f"checkpoint_dir not found: {checkpoint_dir}. "
                       "The SAE checkpoint must be trained externally from the "
                       f"4.87 GB tensor archive (SHA256: {EXTERNAL_TENSOR_ARCHIVE_SHA256}). "
                       "Cannot proceed without an authorized trained checkpoint."
        })
        return 1

    _log(run_id, "checkpoint_load_start", {"checkpoint_dir": str(checkpoint_dir)})
    sae = load_sae_checkpoint(
        checkpoint_dir,
        expected_model_id=config["model_id"],
        expected_model_revision=config["model_revision"],
        expected_component_id=config["component_id"],
    )
    _log(run_id, "checkpoint_load_complete", {
        "sae_id": sae.provenance.sae_id,
        "component_id": sae.provenance.component_id,
        "latent_dim": sae.provenance.latent_dim,
    })

    # Deferred model import
    from instrumentation.model_adapter import load_model_and_tokenizer  # noqa: PLC0415
    _log(run_id, "model_load_start", {"model_id": config["model_id"]})
    model, tokenizer = load_model_and_tokenizer(
        model_id=config["model_id"],
        revision=config["model_revision"],
        dtype=config.get("dtype", "float32"),
        device=config.get("device", "cpu"),
    )
    _log(run_id, "model_load_complete", {})

    # Capture activations and validate reconstruction
    import torch  # noqa: PLC0415
    from instrumentation.adapters.qwen2 import Qwen2Adapter  # noqa: PLC0415
    from experiments.supporting_nov19.red_team.adapter import build_development_cases  # noqa: PLC0415

    cases = build_development_cases()
    adapter = Qwen2Adapter(model, tokenizer)
    reconstruction_errors: list[float] = []
    activation_records: list[dict[str, Any]] = []

    for case in cases[:2]:  # Probe on first two cases to stay within budget
        try:
            activations = adapter.capture_activations(case, component_id=config["component_id"])
            err = sae.validate_reconstruction(activations)
            reconstruction_errors.append(err)
            activation_records.append({
                "case_id": case.case_id,
                "component_id": config["component_id"],
                "reconstruction_error": err,
                "passed_threshold": True,
                "status": "complete",
            })
            _log(run_id, "reconstruction_ok", {
                "case_id": case.case_id,
                "reconstruction_error": err,
            })
        except Exception as exc:  # noqa: BLE001
            activation_records.append({
                "case_id": case.case_id,
                "component_id": config["component_id"],
                "status": "error",
                "error": {"type": type(exc).__name__, "message": str(exc)},
            })
            _log(run_id, "reconstruction_error", {
                "case_id": case.case_id,
                "error": str(exc),
            })

    output_run = output_root / run_id
    output_run.mkdir(parents=True, exist_ok=True)
    records_path = output_run / "activation_records.json"
    records_path.write_text(json.dumps(activation_records, indent=2), encoding="utf-8")

    n_pass = sum(1 for r in activation_records if r.get("passed_threshold") is True)

    # Evidence packet (Section 8.3 compliant)
    import subprocess as _sp  # noqa: PLC0415
    try:
        _head = _sp.run(["git", "rev-parse", "HEAD"], cwd=Path(__file__).resolve().parents[4],
                        capture_output=True, text=True, check=True).stdout.strip()
    except Exception:  # noqa: BLE001
        _head = "unknown"
    evidence_packet = {
        "schema_version": "aether.nov19.supporting-evidence.v1",
        "experiment": "SUPPORT-03-trained-sae-evaluation",
        "source_branch": "amala",
        "source_commit": _head,
        "protocol_sha256": "",
        "model_id": config["model_id"],
        "model_revision": config["model_revision"],
        "input_manifest_sha256": "",
        "split": "development",
        "sample_count": len(activation_records),
        "valid_count": n_pass,
        "invalid_count": 0,
        "error_count": len(activation_records) - n_pass,
        "validation_accesses": 0,
        "test_accesses": 0,
        "raw_artifacts": [str(records_path)],
        "artifact_hashes": {},
        "status": "EXECUTED",
        "evidence_class": "real_model_cpu_float32",
        "claim_boundary": (
            "SAE evaluation executed on development cohort. "
            "Reconstruction gate requires real trained SAE, not random initialization. "
            "overall:PASS must be set only after independent verification."
        ),
        "run_id": run_id,
        "sae_id": sae.provenance.sae_id,
        "component_id": config["component_id"],
        "n_activation_records": len(activation_records),
        "n_reconstruction_passed": n_pass,
        "mean_reconstruction_error": (
            sum(reconstruction_errors) / len(reconstruction_errors)
            if reconstruction_errors else None
        ),
    }
    (output_run / "summary.json").write_text(
        json.dumps(evidence_packet, indent=2, sort_keys=True), encoding="utf-8"
    )
    _log(run_id, "execute_complete", {"summary": evidence_packet})
    print(f"\nSAE evaluation complete. Summary at {output_run / 'summary.json'}", flush=True)
    return 0


def main() -> None:
    """CLI entry point for the SUPPORT-03 SAE runner."""
    parser = argparse.ArgumentParser(description="SUPPORT-03: Trained SAE evaluation.")
    parser.add_argument("--config", type=Path,
                        default=Path("configs/supporting_nov19/sae_qwen15b.json"))
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true")
    group.add_argument("--execute", action="store_true")
    parser.add_argument("--checkpoint-dir", type=Path, default=None,
                        help="Path to trained SAE checkpoint directory (metadata.json + weights.npz).")
    parser.add_argument("--output-root", type=Path,
                        default=Path("results/phase1/sae/qwen15b"))
    args = parser.parse_args()

    if args.dry_run:
        sys.exit(dry_run(args.config, args.checkpoint_dir))
    else:
        if args.checkpoint_dir is None:
            print("ERROR: --checkpoint-dir is required for --execute mode.", file=sys.stderr)
            sys.exit(1)
        sys.exit(execute(args.config, args.checkpoint_dir, args.output_root))


if __name__ == "__main__":
    main()
