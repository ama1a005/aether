"""SUPPORT-01: Real Qwen red-team orchestration runner.

Usage:
    python -m experiments.supporting_nov19.red_team.runner \\
        --config configs/supporting_nov19/red_team_qwen15b.json \\
        --dry-run

    python -m experiments.supporting_nov19.red_team.runner \\
        --config configs/supporting_nov19/red_team_qwen15b.json \\
        --execute \\
        --output-root results/phase1/red_team/qwen15b
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from attacks.corpus.attack_store import AttackStore
from attacks.corpus.builder import CorpusBuilder
from attacks.orchestration import CampaignConfig, run_campaign
from experiments.supporting_nov19.red_team.adapter import (
    RealQwenBackend,
    build_development_cases,
    validate_config,
)

# ---------------------------------------------------------------------------
# Logging helper (structured, no silent swallow)
# ---------------------------------------------------------------------------

def _log(run_id: str, event: str, payload: dict[str, Any]) -> None:
    """Write a structured log line to stdout."""
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "experiment_id": "SUPPORT-01-red-team-qwen15b",
        "component": "red_team_runner",
        "event": event,
        "payload": payload,
    }
    print(json.dumps(record), flush=True)


# ---------------------------------------------------------------------------
# Dry-run mode
# ---------------------------------------------------------------------------

def dry_run(config_path: Path) -> int:
    """Validate config, prerequisites and directory state. No model loading.

    Returns 0 on success, 1 on validation failure.
    """
    run_id = f"dry_{uuid.uuid4().hex[:8]}"
    _log(run_id, "dry_run_start", {"config": str(config_path)})

    if not config_path.is_file():
        _log(run_id, "dry_run_error", {"message": f"Config not found: {config_path}"})
        return 1

    config = json.loads(config_path.read_text(encoding="utf-8"))
    errors = validate_config(config)
    if errors:
        _log(run_id, "dry_run_failed", {"errors": errors})
        print(f"\nDry-run FAILED: {len(errors)} validation error(s):", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    # Check source commit matches expected
    import subprocess  # noqa: PLC0415
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(__file__).resolve().parents[4],
            check=True, capture_output=True, text=True,
        )
        head = result.stdout.strip()
        _log(run_id, "dry_run_git_head", {"head": head,
             "expected_source": config.get("source_commit")})
    except Exception as exc:  # noqa: BLE001
        _log(run_id, "dry_run_git_warning", {"message": str(exc)})

    _log(run_id, "dry_run_ok", {
        "model_id": config["model_id"],
        "model_revision": config["model_revision"],
        "split": config["split"],
        "attack_families": config["attack_families"],
        "max_target_calls": config["max_target_calls"],
        "seed": config["seed"],
        "output_dir": config["output_dir"],
    })
    print("\nDry-run PASSED: config and prerequisites validated.", flush=True)
    return 0


# ---------------------------------------------------------------------------
# Execute mode
# ---------------------------------------------------------------------------

def execute(config_path: Path, output_root: Path) -> int:
    """Load the pinned real Qwen once and run the full red-team campaign.

    Returns 0 on success (campaign run completed; individual attempt errors
    are recorded as evidence, not suppressed).  Returns 1 on fatal setup errors.
    Real-model mode fails closed; no silent fallback to mock outputs.
    """
    run_id = f"rt_{uuid.uuid4().hex[:12]}"
    _log(run_id, "execute_start", {"config": str(config_path), "output_root": str(output_root)})

    if not config_path.is_file():
        _log(run_id, "execute_error", {"message": f"Config not found: {config_path}"})
        return 1

    config = json.loads(config_path.read_text(encoding="utf-8"))
    errors = validate_config(config)
    if errors:
        _log(run_id, "execute_failed_validation", {"errors": errors})
        return 1

    backend = RealQwenBackend(
        model_id=config["model_id"],
        model_revision=config["model_revision"],
        tokenizer_revision=config["tokenizer_revision"],
        dtype=config.get("dtype", "float32"),
        device=config.get("device", "cpu"),
    )

    _log(run_id, "model_load_start", {"model_id": config["model_id"],
                                      "model_revision": config["model_revision"]})
    backend.load()
    _log(run_id, "model_load_complete", {})

    campaign = CampaignConfig(
        experiment_id=f"SUPPORT01_{run_id}",
        seed=config["seed"],
        max_target_calls=config["max_target_calls"],
        split=config["split"],
    )

    cases = build_development_cases()
    _log(run_id, "cases_loaded", {"n_cases": len(cases),
                                   "case_ids": [c.case_id for c in cases]})

    store_path = output_root / f"{run_id}_corpus"
    store = AttackStore(str(store_path))
    n_per_family = max(1, config["max_target_calls"] // (2 * 4))
    attacks = CorpusBuilder(campaign.seed).build_phase1_corpus(store, n_per_family)
    _log(run_id, "attack_corpus_built", {"n_attacks": len(attacks)})

    output_dir = output_root / run_id
    _log(run_id, "campaign_start", {"output_dir": str(output_dir)})

    summary = run_campaign(backend, cases, attacks, campaign, output_dir)
    _log(run_id, "campaign_complete", {"summary": summary})
    print(f"\nCampaign complete. Summary written to {output_dir / 'summary.json'}", flush=True)
    return 0


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """CLI entry point for the SUPPORT-01 red-team runner."""
    parser = argparse.ArgumentParser(
        description="SUPPORT-01: Real Qwen red-team orchestration runner."
    )
    parser.add_argument("--config", type=Path,
                        default=Path("configs/supporting_nov19/red_team_qwen15b.json"),
                        help="Path to the prospective run config JSON.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true",
                       help="Validate config and prerequisites; do not load the model.")
    group.add_argument("--execute", action="store_true",
                       help="Load the pinned real Qwen and run the campaign.")
    parser.add_argument("--output-root", type=Path,
                        default=Path("results/phase1/red_team/qwen15b"),
                        help="Root directory for campaign outputs (--execute only).")
    args = parser.parse_args()

    if args.dry_run:
        sys.exit(dry_run(args.config))
    else:
        sys.exit(execute(args.config, args.output_root))


if __name__ == "__main__":
    main()
