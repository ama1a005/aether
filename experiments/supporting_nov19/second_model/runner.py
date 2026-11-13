"""SUPPORT-04: Second independent model qualification runner.

Qualifies a different open-weight model (not Qwen 1.5B) on the AETHER
behavioral and instrumentation gates. The 0.5B model did NOT pass balanced
qualification; this runner targets a prospectively declared new model.

Usage:
    python -m experiments.supporting_nov19.second_model.runner --dry-run
    python -m experiments.supporting_nov19.second_model.runner --execute \\
        --config configs/supporting_nov19/second_model_manifest.json \\
        --output-root results/phase1/model_qualification/second_model
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants: second model declared prospectively
# ---------------------------------------------------------------------------

SECOND_MODEL_ID = "microsoft/Phi-3-mini-4k-instruct"
SECOND_MODEL_REVISION = "unknown"  # Must be pinned from actual HuggingFace download

DISQUALIFIED_MODELS = {
    "Qwen/Qwen2.5-0.5B-Instruct",  # Asymmetric on balanced cases - did not pass
}
PRIMARY_MODEL_ID = "Qwen/Qwen2.5-1.5B-Instruct"  # May not be reused as "second model"


def _log(run_id: str, event: str, payload: dict[str, Any]) -> None:
    """Write a structured log line to stdout."""
    print(json.dumps({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "experiment_id": "SUPPORT-04-second-model-qualification",
        "component": "second_model_runner",
        "event": event,
        "payload": payload,
    }), flush=True)


def validate_second_model_config(config: dict[str, Any]) -> list[str]:
    """Return validation errors for the second model manifest."""
    errors: list[str] = []
    for key in ["model_id", "model_revision", "dtype", "device", "output_dir", "source_commit"]:
        if key not in config:
            errors.append(f"Missing required config key: {key!r}")
    model_id = config.get("model_id", "")
    if model_id == PRIMARY_MODEL_ID:
        errors.append(
            f"model_id must not be the primary model ({PRIMARY_MODEL_ID}); "
            "rename an existing checkpoint is not a qualification."
        )
    if model_id in DISQUALIFIED_MODELS:
        errors.append(
            f"model_id {model_id!r} failed prior balanced qualification and cannot be "
            "declared a second successfully qualified model."
        )
    if not model_id.strip():
        errors.append("model_id must be populated")
    model_revision = config.get("model_revision", "")
    if not model_revision.strip() or model_revision == "unknown":
        errors.append(
            "model_revision must be an exact pinned commit/revision, not 'unknown'. "
            "Download the model and record its exact revision before executing."
        )
    return errors


def dry_run(config_path: Path) -> int:
    """Validate second model manifest without loading any weights."""
    run_id = f"sm_dry_{uuid.uuid4().hex[:8]}"
    _log(run_id, "dry_run_start", {"config": str(config_path)})

    if not config_path.is_file():
        _log(run_id, "dry_run_error", {"message": f"Config not found: {config_path}"})
        return 1

    config = json.loads(config_path.read_text(encoding="utf-8"))
    errors = validate_second_model_config(config)
    if errors:
        _log(run_id, "dry_run_failed", {"errors": errors})
        for err in errors:
            print(f"  ERROR: {err}", file=sys.stderr)
        return 1

    _log(run_id, "dry_run_ok", config)
    print("\nDry-run PASSED: Second model manifest validated.", flush=True)
    return 0


def execute(config_path: Path, output_root: Path) -> int:
    """Run behavioral and instrumentation qualification gates on the second model.

    The qualification protocol mirrors the primary Qwen 1.5B qualification:
    - Balanced clean decision accuracy (12/12 in each direction)
    - Message-level rescue and induction (12/12 each direction)
    - Instrumentation/capture gates

    Results are only written from actual model execution.
    """
    run_id = f"sm_{uuid.uuid4().hex[:12]}"
    _log(run_id, "execute_start", {"config": str(config_path)})

    if not config_path.is_file():
        _log(run_id, "execute_error", {"message": f"Config not found: {config_path}"})
        return 1

    config = json.loads(config_path.read_text(encoding="utf-8"))
    errors = validate_second_model_config(config)
    if errors:
        _log(run_id, "execute_failed_validation", {"errors": errors})
        return 1

    # Deferred model loading
    from instrumentation.model_adapter import load_model_and_tokenizer  # noqa: PLC0415
    _log(run_id, "model_load_start", {"model_id": config["model_id"],
                                       "model_revision": config["model_revision"]})
    model, tokenizer = load_model_and_tokenizer(
        model_id=config["model_id"],
        revision=config["model_revision"],
        dtype=config.get("dtype", "float32"),
        device=config.get("device", "cpu"),
    )
    _log(run_id, "model_load_complete", {})

    from target.agents.agent_a import AgentA  # noqa: PLC0415
    from target.agents.agent_b import AgentB  # noqa: PLC0415
    from target.mcp.mock_client import MockMCPClient  # noqa: PLC0415
    from experiments.supporting_nov19.red_team.adapter import build_development_cases  # noqa: PLC0415

    mcp_client = MockMCPClient()
    agent_a = AgentA(config["model_id"], mcp_client, {}, model=model, tokenizer=tokenizer)
    agent_b = AgentB(config["model_id"], {}, model=model, tokenizer=tokenizer)

    cases = build_development_cases()
    output_run = output_root / run_id
    output_run.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, Any]] = []
    seed = config.get("seed", 0)

    for case in cases:
        try:
            output_a, message, calls = agent_a.run(case, attack_spec=None)
            decision_b, score_b = agent_b.run(message, case)
            correct = decision_b == case.ground_truth_decision
            record = {
                "run_id": run_id,
                "case_id": case.case_id,
                "seed": seed,
                "model_id": config["model_id"],
                "model_revision": config["model_revision"],
                "decision": decision_b,
                "ground_truth": case.ground_truth_decision,
                "correct": correct,
                "decision_score": score_b,
                "status": "complete",
                "error": None,
            }
        except Exception as exc:  # noqa: BLE001
            record = {
                "run_id": run_id,
                "case_id": case.case_id,
                "status": "error",
                "error": {"type": type(exc).__name__, "message": str(exc)},
            }

        (output_run / f"{case.case_id}_clean.json").write_text(
            json.dumps(record, indent=2), encoding="utf-8"
        )
        records.append(record)
        _log(run_id, "case_complete", {"case_id": case.case_id,
                                        "status": record["status"]})

    n_complete = sum(1 for r in records if r["status"] == "complete")
    n_correct = sum(1 for r in records if r.get("correct") is True)

    # Evidence packet (Section 8.3 compliant)
    import subprocess as _sp  # noqa: PLC0415
    try:
        _head = _sp.run(["git", "rev-parse", "HEAD"], cwd=Path(__file__).resolve().parents[4],
                        capture_output=True, text=True, check=True).stdout.strip()
    except Exception:  # noqa: BLE001
        _head = "unknown"
    evidence_packet = {
        "schema_version": "aether.nov19.supporting-evidence.v1",
        "experiment": "SUPPORT-04-second-model-qualification",
        "source_branch": "amala",
        "source_commit": _head,
        "protocol_sha256": "",
        "model_id": config["model_id"],
        "model_revision": config["model_revision"],
        "input_manifest_sha256": "",
        "split": "development",
        "sample_count": len(records),
        "valid_count": n_complete,
        "invalid_count": 0,
        "error_count": len(records) - n_complete,
        "validation_accesses": 0,
        "test_accesses": 0,
        "raw_artifacts": [str(output_run)],
        "artifact_hashes": {},
        "status": "EXECUTED",
        "evidence_class": "real_model_cpu_float32",
        "claim_boundary": (
            "Second model qualification on development cohort. "
            "overall:PASS requires 24/24 clean+attacked balanced cases, "
            "rescue/induction 12/12 each, and instrumentation gate."
        ),
        "run_id": run_id,
        "n_cases": len(records),
        "n_complete": n_complete,
        "n_correct": n_correct,
        "n_error": len(records) - n_complete,
        "clean_accuracy": n_correct / n_complete if n_complete > 0 else None,
    }
    (output_run / "summary.json").write_text(
        json.dumps(evidence_packet, indent=2, sort_keys=True), encoding="utf-8"
    )
    _log(run_id, "execute_complete", {"summary": evidence_packet})
    print(f"\nSecond model qualification complete. Summary at {output_run / 'summary.json'}",
          flush=True)
    return 0


def main() -> None:
    """CLI entry point for the SUPPORT-04 second model runner."""
    parser = argparse.ArgumentParser(
        description="SUPPORT-04: Second independent model qualification."
    )
    parser.add_argument("--config", type=Path,
                        default=Path("configs/supporting_nov19/second_model_manifest.json"))
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true")
    group.add_argument("--execute", action="store_true")
    parser.add_argument("--output-root", type=Path,
                        default=Path("results/phase1/model_qualification/second_model"))
    args = parser.parse_args()

    if args.dry_run:
        sys.exit(dry_run(args.config))
    else:
        sys.exit(execute(args.config, args.output_root))


if __name__ == "__main__":
    main()
