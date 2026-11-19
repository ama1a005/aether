"""Run the deterministic target harness and retain an auditable trace bundle."""

from __future__ import annotations

import argparse
import csv
import dataclasses
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import uuid

import yaml

from contracts.schemas import AttackSpec, RunTrace
from target.case_loader import CaseLoader
from target.mcp.mock_client import MockMCPClient
from target.mcp.tools import get_ecg_analysis, get_vital_signs
from target.agents.agent_a import AgentA
from target.agents.agent_b import AgentB
from target.trace_logger import TraceLogger
from target.decision_parser import DecisionParser


def _sha256_bytes(value: bytes) -> str:
    """Return a SHA-256 digest for one in-memory artifact."""
    return hashlib.sha256(value).hexdigest()


def _atomic_json(path: Path, value: dict) -> None:
    """Write one JSON artifact atomically without replacing an existing file."""
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        if path.exists():
            raise FileExistsError(path)
        os.rename(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _git_value(*arguments: str) -> str:
    """Return one required Git value from the repository containing this file."""
    root = Path(__file__).resolve().parents[1]
    return subprocess.run(
        ["git", *arguments], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


def _write_structured_log(run_id: str, experiment_id: str, event: str,
                          payload: dict) -> None:
    """Emit one machine-readable target-harness lifecycle event."""
    print(json.dumps({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "experiment_id": experiment_id,
        "component": "target_runner",
        "event": event,
        "payload": payload,
    }, sort_keys=True), flush=True)


def main() -> None:
    """Run clean and attacked pairs from a validated experiment configuration."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ValueError("target experiment config must be a YAML mapping")

    case_type = config.get("case_source", {}).get("type", "fixture")
    case_loader = CaseLoader(source=case_type)

    mcp_client = MockMCPClient()
    mcp_client.register_tool("get_ecg_analysis", get_ecg_analysis)
    mcp_client.register_tool("get_vital_signs", get_vital_signs)

    model_config = config.get("model", {})
    model_a = model_config.get("agent_a", "model_a")
    model_b = model_config.get("agent_b", "model_b")

    agent_a = AgentA(model_id=model_a, mcp_client=mcp_client, config=config)
    agent_b = AgentB(model_id=model_b, config=config)

    poison_spec_value = config.get("attack", {}).get("poison_spec")
    if not poison_spec_value:
        raise ValueError("target experiment config must declare attack.poison_spec")
    poison_spec_path = Path(poison_spec_value)
    if not poison_spec_path.is_absolute():
        poison_spec_path = (Path.cwd() / poison_spec_path).resolve()
    if not poison_spec_path.is_file():
        raise FileNotFoundError(f"configured target attack spec does not exist: {poison_spec_path}")
    attack_spec_data = json.loads(poison_spec_path.read_text(encoding="utf-8"))
    attack_spec = AttackSpec.from_dict(attack_spec_data)

    base_trace_dir = Path(config.get("output", {}).get("trace_dir", "results/raw"))
    run_id = f"{config.get('experiment_id', 'P0_target_review')}_{uuid.uuid4().hex}"
    trace_dir = base_trace_dir / run_id
    if trace_dir.exists():
        raise FileExistsError(f"target run output already exists: {trace_dir}")
    trace_dir.mkdir(parents=True)
    trace_logger = TraceLogger(output_dir=str(trace_dir))
    decision_parser = DecisionParser()

    n_cases = config.get("n_cases", 5)
    seed = config.get("seed", 42)
    cases = case_loader.load_cases(n=n_cases, seed=seed)

    results = []
    experiment_id = str(config.get("experiment_id", f"P0_target_{run_id}"))
    _write_structured_log(run_id, experiment_id, "run_started", {
        "config_file": str(config_path), "case_count": len(cases), "seed": seed,
        "case_source": case_type,
    })

    for case in cases:
        for mode in ["clean", "attacked"]:
            current_attack_spec = attack_spec if mode == 'attacked' else None

            out_a, msg_a, tool_calls = agent_a.run(case=case, attack_spec=current_attack_spec)
            out_b, score = agent_b.run(message=msg_a, case=case)
            decision, parsed_score = decision_parser.parse(out_b, msg_a.structured_payload)

            attack_success = False
            if mode == 'attacked' and current_attack_spec:
                attack_success = decision_parser.is_attack_success(decision, current_attack_spec)

            trace = RunTrace(
                run_id=msg_a.run_id,
                case_id=case.case_id,
                seed=seed,
                model_ids={"agent_a": model_a, "agent_b": model_b},
                messages=[dataclasses.asdict(msg_a)],
                tool_calls=tool_calls,
                final_decision=decision,
                attack_id=current_attack_spec.attack_id if current_attack_spec else None,
                decision_score=parsed_score,
                attack_success=attack_success,
            )
            trace_path = trace_logger.log(trace)
            results.append({
                "case_id": case.case_id,
                "mode": mode,
                "expected": case.ground_truth_decision,
                "decision": decision,
                "attack_success": attack_success,
                "trace_path": trace_path
            })
            _write_structured_log(run_id, experiment_id, "case_condition_complete", {
                "case_id": case.case_id, "condition": mode,
                "decision": decision, "trace_path": trace_path,
            })

    clean_runs = [row for row in results if row["mode"] == "clean"]
    attacked_runs = [row for row in results if row["mode"] == "attacked"]
    clean_pass = sum(row["decision"] == row["expected"] for row in clean_runs)
    attack_success_count = sum(row["attack_success"] for row in attacked_runs)

    csv_path = trace_dir / "results.csv"
    with csv_path.open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "case_id", "mode", "expected", "decision", "attack_success", "trace_path"
        ])
        writer.writeheader()
        writer.writerows(results)

    source_hash = _sha256_bytes(json.dumps(
        [dataclasses.asdict(case) for case in cases], sort_keys=True,
        separators=(",", ":"), allow_nan=False,
    ).encode("utf-8"))
    freeze = subprocess.run(
        [sys.executable, "-m", "pip", "freeze", "--all"],
        check=True, capture_output=True, text=True,
    ).stdout
    root = Path(__file__).resolve().parents[1]
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=root, check=True,
        capture_output=True, text=True,
    ).stdout
    artifact_paths = sorted(path for path in trace_dir.iterdir() if path.is_file())
    metadata = {
        "schema_version": "aether.target-run-manifest.v1",
        "run_id": run_id,
        "experiment_id": experiment_id,
        "utc_timestamp": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git_value("rev-parse", "HEAD"),
        "uncommitted_diff": bool(status),
        "dataset_manifest_hashes": {
            "generated_cases_sha256": source_hash,
            "attack_spec_sha256": hashlib.sha256(poison_spec_path.read_bytes()).hexdigest(),
        },
        "model_id": f"{model_a}+{model_b}",
        "model_revision": str(model_config.get("revision", "rule_based")),
        "tokenizer_revision": str(model_config.get("tokenizer_revision", "not_applicable_rule_based")),
        "prompt_versions": config.get("prompt_versions", {"target": "deterministic_rules_v1"}),
        "random_seeds": [seed],
        "hardware": platform.platform(),
        "python_env_hash": _sha256_bytes(freeze.encode("utf-8")),
        "command_line": sys.argv,
        "config_file": str(config_path),
        "config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
        "raw_output_path": str(trace_dir.resolve()),
        "artifact_paths": [str(path.resolve()) for path in artifact_paths],
        "artifact_sha256": {str(path.relative_to(trace_dir)): hashlib.sha256(path.read_bytes()).hexdigest()
                            for path in artifact_paths},
        "clean_correct": clean_pass,
        "clean_total": len(clean_runs),
        "attack_successes": attack_success_count,
        "attack_attempts": len(attacked_runs),
        "claim_boundary": "Deterministic target plumbing only; not model or benchmark evidence.",
    }
    _atomic_json(trace_dir / "manifest.json", metadata)
    _write_structured_log(run_id, experiment_id, "run_complete", {
        "raw_output_path": str(trace_dir.resolve()),
        "clean_correct": clean_pass, "clean_total": len(clean_runs),
        "attack_successes": attack_success_count, "attack_attempts": len(attacked_runs),
    })
    clean_rate = clean_pass / len(clean_runs) if clean_runs else 0.0
    attack_rate = attack_success_count / len(attacked_runs) if attacked_runs else 0.0
    print(f"Clean Pass Rate: {clean_rate:.1%} ({clean_pass}/{len(clean_runs)})")
    print(
        "Attack Success Rate: "
        f"{attack_rate:.1%} ({attack_success_count}/{len(attacked_runs)})"
    )

if __name__ == "__main__":
    main()
