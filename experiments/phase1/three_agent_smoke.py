"""Manifest-backed synthetic acceptance for the mandatory Agent C path."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
from time import perf_counter
from uuid import uuid4
import yaml

from contracts.schemas import PatientCase
from experiments.manifest import create_run_manifest, write_run_manifest
from target.agents.agent_a import AgentA
from target.agents.agent_b import AgentB
from target.agents.agent_c import AgentC
from target.mcp.mock_client import MockMCPClient
from target.mcp.tools import get_ecg_analysis, get_vital_signs
from target.three_agent_pipeline import run_three_agent_pipeline

ROOT = Path(__file__).resolve().parents[2]


def run(config_path: Path, output_root: Path | None = None) -> Path:
    """Execute a synthetic three-agent review and write raw evidence/manifest."""
    config_path = config_path.resolve()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if config["evidence_class"] != "synthetic_acceptance_only" or config["split"] != "synthetic":
        raise ValueError("Three-agent smoke accepts synthetic configurations only")
    started = perf_counter()
    mcp = MockMCPClient()
    mcp.register_tool("get_ecg_analysis", get_ecg_analysis)
    mcp.register_tool("get_vital_signs", get_vital_signs)
    case = PatientCase("three-agent-smoke", {"heart_rate": 130, "spo2": 90}, "ESCALATE",
                       source_dataset="synthetic", source_split="synthetic", fixture_only=True)
    result = run_three_agent_pipeline(case, AgentA("deterministic-a", mcp, {}),
                                      AgentB("deterministic-b", {}),
                                      AgentC("deterministic-c", {"use_verification_tool": True}, mcp))
    checks = {"agent_b_escalates": result.agent_b_decision == "ESCALATE",
              "agent_c_escalates": result.review.reviewed_decision == "ESCALATE",
              "agent_c_tool_logged": len(result.review.tool_calls) == 1,
              "agent_a_evidence_preserved": len(result.agent_a_tool_calls) == 2}
    run_id = f"{config['experiment_id']}_{uuid4().hex}"
    destination = (output_root or ROOT / config["output_root"]) / run_id
    destination.mkdir(parents=True, exist_ok=False)
    output = destination / "results.json"
    payload = {"run_id": run_id, "utc_timestamp": datetime.now(timezone.utc).isoformat(),
               "evidence_class": config["evidence_class"], "checks": checks,
               "raw_result": asdict(result), "validation_executions": 0, "test_executions": 0,
               "claim_limit": "Synthetic deterministic Agent C acceptance only."}
    output.write_text(json.dumps(payload, indent=2, allow_nan=False), encoding="utf-8")
    manifest = create_run_manifest(
        experiment_id=config["experiment_id"], run_id=run_id,
        model_id="deterministic_three_agent", model_revision="v1", tokenizer_revision="not_applicable",
        dataset_id="synthetic_three_agent_acceptance", dataset_version="v1", dataset_split="synthetic",
        subset_ids=[case.case_id], seeds=[config["seed"]], config_file=config_path,
        raw_output_path=output, dataset_files=[Path(__file__).resolve()],
        prompt_files=[], intervention_config={"agent_c_verification_tool": "get_vital_signs"},
        artifact_paths=[output, ROOT / "target/agents/agent_c.py"],
        timing_seconds={"execution": perf_counter() - started}, repository=ROOT)
    write_run_manifest(manifest, destination / "manifest.json")
    if not all(checks.values()):
        raise RuntimeError(f"Three-agent acceptance failed; evidence saved in {destination}")
    return destination


def main() -> None:
    """Run configured acceptance and print its artifact directory."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path,
                        default=ROOT / "configs/experiments/three_agent_synthetic.yaml")
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args()
    print(f"THREE AGENT ACCEPTANCE PASSED: {run(args.config, args.output_root)}")


if __name__ == "__main__":
    main()
