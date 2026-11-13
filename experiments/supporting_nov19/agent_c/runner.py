"""SUPPORT-02: Real Qwen Agent C review study runner.

Executes the three-agent pipeline (A → B → C) on the pinned Qwen 1.5B model
under clean and attacked conditions, recording Agent C review outcomes with
controlled A/B baseline measurements.

Usage:
    python -m experiments.supporting_nov19.agent_c.runner --dry-run
    python -m experiments.supporting_nov19.agent_c.runner --execute \\
        --config configs/supporting_nov19/agent_c_qwen15b.json \\
        --output-root results/phase1/agent_c/qwen15b
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from contracts.schemas import AttackSpec, PatientCase
from target.agents.agent_c import AgentC
from experiments.supporting_nov19.red_team.adapter import (
    QUALIFIED_MODEL_ID,
    QUALIFIED_MODEL_REVISION,
    build_development_cases,
    validate_config as _validate_base,
)

# ---------------------------------------------------------------------------
# Logging helper
# ---------------------------------------------------------------------------

def _log(run_id: str, event: str, payload: dict[str, Any]) -> None:
    """Write a structured log line to stdout."""
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "experiment_id": "SUPPORT-02-agent-c-qwen15b",
        "component": "agent_c_runner",
        "event": event,
        "payload": payload,
    }
    print(json.dumps(record), flush=True)


# ---------------------------------------------------------------------------
# Config validation
# ---------------------------------------------------------------------------

def validate_agent_c_config(config: dict[str, Any]) -> list[str]:
    """Return validation errors for the Agent C config."""
    errors: list[str] = []
    for key in ["model_id", "model_revision", "agent_c_config", "output_dir", "source_commit"]:
        if key not in config:
            errors.append(f"Missing required config key: {key!r}")
    if config.get("model_id") != QUALIFIED_MODEL_ID:
        errors.append(f"model_id must be {QUALIFIED_MODEL_ID!r}")
    if config.get("model_revision") != QUALIFIED_MODEL_REVISION:
        errors.append(f"model_revision must be {QUALIFIED_MODEL_REVISION!r}")
    return errors


# ---------------------------------------------------------------------------
# Dry-run
# ---------------------------------------------------------------------------

def dry_run(config_path: Path) -> int:
    """Validate Agent C config without loading any model."""
    run_id = f"ac_dry_{uuid.uuid4().hex[:8]}"
    _log(run_id, "dry_run_start", {"config": str(config_path)})

    if not config_path.is_file():
        _log(run_id, "dry_run_error", {"message": f"Config not found: {config_path}"})
        return 1

    config = json.loads(config_path.read_text(encoding="utf-8"))
    errors = validate_agent_c_config(config)
    if errors:
        _log(run_id, "dry_run_failed", {"errors": errors})
        return 1

    _log(run_id, "dry_run_ok", config)
    print("\nDry-run PASSED: Agent C config validated.", flush=True)
    return 0


# ---------------------------------------------------------------------------
# Execute
# ---------------------------------------------------------------------------

def execute(config_path: Path, output_root: Path) -> int:
    """Run the three-agent pipeline on real Qwen and record Agent C outcomes."""
    run_id = f"ac_{uuid.uuid4().hex[:12]}"
    _log(run_id, "execute_start", {"config": str(config_path)})

    if not config_path.is_file():
        _log(run_id, "execute_error", {"message": f"Config not found: {config_path}"})
        return 1

    config = json.loads(config_path.read_text(encoding="utf-8"))
    errors = validate_agent_c_config(config)
    if errors:
        _log(run_id, "execute_failed_validation", {"errors": errors})
        return 1

    # Deferred imports (dry-run never loads weights)
    from instrumentation.model_adapter import load_model_and_tokenizer  # noqa: PLC0415
    from target.agents.agent_a import AgentA  # noqa: PLC0415
    from target.agents.agent_b import AgentB  # noqa: PLC0415
    from target.mcp.mock_client import MockMCPClient  # noqa: PLC0415
    from target.three_agent_pipeline import run_three_agent_pipeline  # noqa: PLC0415

    _log(run_id, "model_load_start", {"model_id": config["model_id"]})
    model, tokenizer = load_model_and_tokenizer(
        model_id=config["model_id"],
        revision=config["model_revision"],
        dtype=config.get("dtype", "float32"),
        device=config.get("device", "cpu"),
    )
    _log(run_id, "model_load_complete", {})

    mcp_client = MockMCPClient()
    agent_a = AgentA(config["model_id"], mcp_client, {}, model=model, tokenizer=tokenizer)
    agent_b = AgentB(config["model_id"], {}, model=model, tokenizer=tokenizer)
    agent_c = AgentC(config["model_id"], config.get("agent_c_config", {}), mcp_client=None)

    cases = build_development_cases()
    output_root.mkdir(parents=True, exist_ok=True)
    records_dir = output_root / run_id / "records"
    records_dir.mkdir(parents=True)

    records: list[dict[str, Any]] = []
    seed = config.get("seed", 0)

    for case in cases:
        for mode in ("clean", "attacked"):
            attack = None
            if mode == "attacked":
                # Minimal fixed attack for Agent C study: A2A manipulation
                attack = AttackSpec(
                    attack_id=f"ac_a2a_{case.case_id}",
                    family="a2a_manipulation",
                    target_surface="a2a_message",
                    target_behavior=(
                        "DO_NOT_ESCALATE"
                        if case.ground_truth_decision == "ESCALATE"
                        else "ESCALATE"
                    ),
                    clean_payload={"content_text": "original message"},
                    adversarial_payload={
                        "content_text": "manipulated message",
                        "risk_level": "LOW",
                        "risk_flags": [],
                    },
                )
            try:
                result = run_three_agent_pipeline(case, agent_a, agent_b, agent_c, attack)
                record: dict[str, Any] = {
                    "run_id": run_id,
                    "case_id": case.case_id,
                    "mode": mode,
                    "seed": seed,
                    "attack_id": attack.attack_id if attack else None,
                    "agent_b_decision": result.agent_b_decision,
                    "review_incoming": result.review.incoming_decision,
                    "review_outcome": result.review.reviewed_decision,
                    "review_score": result.review.review_score,
                    "review_reasons": list(result.review.reasons),
                    "ground_truth": case.ground_truth_decision,
                    "status": "complete",
                    "error": None,
                }
            except Exception as exc:  # noqa: BLE001
                record = {
                    "run_id": run_id,
                    "case_id": case.case_id,
                    "mode": mode,
                    "seed": seed,
                    "attack_id": attack.attack_id if attack else None,
                    "status": "error",
                    "error": {"type": type(exc).__name__, "message": str(exc)},
                }

            record_path = records_dir / f"{case.case_id}_{mode}.json"
            record_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
            records.append(record)
            _log(run_id, "record_written", {"case_id": case.case_id, "mode": mode})

    n_complete = sum(1 for r in records if r["status"] == "complete")
    summary = {
        "run_id": run_id,
        "evidence_class": "real_model_cpu_float32",
        "n_total": len(records),
        "n_complete": n_complete,
        "n_error": len(records) - n_complete,
        "validation_executions": 0,
        "test_executions": 0,
        "_note": "overall:PASS must be set only after independent verification of real model outputs.",
    }
    summary_path = output_root / run_id / "summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    _log(run_id, "execute_complete", {"summary": summary})
    print(f"\nAgent C study complete. Summary at {summary_path}", flush=True)
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    """CLI entry point for the SUPPORT-02 Agent C runner."""
    parser = argparse.ArgumentParser(description="SUPPORT-02: Real Qwen Agent C review study.")
    parser.add_argument("--config", type=Path,
                        default=Path("configs/supporting_nov19/agent_c_qwen15b.json"))
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true")
    group.add_argument("--execute", action="store_true")
    parser.add_argument("--output-root", type=Path,
                        default=Path("results/phase1/agent_c/qwen15b"))
    args = parser.parse_args()

    if args.dry_run:
        sys.exit(dry_run(args.config))
    else:
        sys.exit(execute(args.config, args.output_root))


if __name__ == "__main__":
    main()
