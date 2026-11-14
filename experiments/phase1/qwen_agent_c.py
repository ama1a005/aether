"""Apply the frozen deterministic Agent-C review to retained real-Qwen traces."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
from typing import Any, Sequence

import yaml

from contracts.schemas import A2AMessageRecord, PatientCase
from target.agents.agent_c import AgentC
from target.mcp.mock_client import MockMCPClient
from target.mcp.tools import get_vital_signs
from experiments.external_bundle import runtime_metadata, sha256_file, verify_protocol_approval, write_bundle_manifest


ROOT = Path(__file__).resolve().parents[2]


def evaluate(rows: Sequence[dict[str, Any]], registry: Sequence[dict[str, Any]], threshold: float) -> dict[str, Any]:
    """Review attacked Qwen decisions while preserving every input and error row."""
    cases = {str(case["case_id"]): case for case in registry}
    if len(rows) != len(cases) or not rows:
        raise ValueError("Agent-C evaluation requires the complete frozen Qwen cohort")
    mcp = MockMCPClient()
    mcp.register_tool("get_vital_signs", get_vital_signs)
    agent = AgentC("deterministic-agent-c-v1", {"use_verification_tool": True, "risk_score_threshold": threshold}, mcp)
    outputs = []
    for row in rows:
        case = cases.get(str(row.get("case_id")))
        if case is None or case.get("split") != "development":
            raise ValueError("Qwen row is absent from the frozen development registry")
        message = row.get("attacked_message")
        incoming = row.get("attacked_receiver_code")
        if not isinstance(message, dict) or message.get("valid") is not True or incoming not in {"A", "B"}:
            outputs.append({"case_id": row.get("case_id"), "valid": False, "error": "invalid_qwen_trace"})
            continue
        structured = {"risk_level": "LOW", "risk_flags": [], "decision_code": message.get("decision_code")}
        record = A2AMessageRecord(f"agent-c-{row['case_id']}", "retained-qwen", "agent-a", "agent-b",
                                  json.dumps(message, sort_keys=True), structured,
                                  provenance={"source": "retained_real_qwen_mq_g1"})
        patient = PatientCase(str(case["case_id"]), dict(case["features"]),
                              str(case["ground_truth_decision"]), source_dataset=str(case["dataset_version"]),
                              source_split="development", fixture_only=False)
        review = agent.run("ESCALATE" if incoming == "A" else "DO_NOT_ESCALATE", record, patient)
        expected = patient.ground_truth_decision
        outputs.append({"case_id": patient.case_id, "valid": True,
                        "incoming_decision": review.incoming_decision,
                        "reviewed_decision": review.reviewed_decision,
                        "ground_truth_decision": expected,
                        "incoming_correct": review.incoming_decision == expected,
                        "reviewed_correct": review.reviewed_decision == expected,
                        "review": asdict(review)})
    valid = [row for row in outputs if row["valid"]]
    if not valid:
        raise ValueError("Agent-C evaluation produced no valid rows")
    return {"rows": outputs, "counts": {"total": len(outputs), "valid": len(valid),
            "invalid": len(outputs) - len(valid),
            "incoming_correct": sum(row["incoming_correct"] for row in valid),
            "reviewed_correct": sum(row["reviewed_correct"] for row in valid)}}


def run(config_path: Path, approval_path: Path, output: Path) -> Path:
    """Execute an approved development-only post-hoc review protocol."""
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    verify_protocol_approval(config_path, approval_path)
    if config.get("status") != "awaiting_human_protocol_review":
        raise ValueError("unexpected Agent-C proposal status")
    if config.get("split") != "development" or config.get("validation_executions") != 0 or config.get("test_executions") != 0:
        raise PermissionError("Agent-C protocol attempts protected-split access")
    rows = json.loads((ROOT / config["qwen_rows"]).read_text(encoding="utf-8"))
    registry = json.loads((ROOT / config["case_registry"]).read_text(encoding="utf-8"))["cases"]
    result = evaluate(rows, registry, float(config["risk_score_threshold"]))
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    destination = output / "raw_reviews.json"
    destination.write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
    summary = {"overall": "PASS", "evidence_origin": "retained_real_qwen_plus_deterministic_agent_c",
               "model_id": "Qwen/Qwen2.5-1.5B-Instruct", **result["counts"],
               "validation_executions": 0, "test_executions": 0}
    (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    metadata = runtime_metadata(
        repository=ROOT, experiment_id="P0_agent_c_qwen15b_development", run_id=output.name,
        dataset_manifest_hashes={config["qwen_rows"]: sha256_file(ROOT / config["qwen_rows"]),
                                 config["case_registry"]: sha256_file(ROOT / config["case_registry"])},
        model_id="Qwen/Qwen2.5-1.5B-Instruct",
        model_revision="989aa7980e4cf806f80c7fef2b1adb7bc71aa306",
        tokenizer_revision="989aa7980e4cf806f80c7fef2b1adb7bc71aa306", seeds=[0],
        config_file=config_path, evidence_kind="qwen_agent_c")
    write_bundle_manifest(output, metadata)
    return destination


def main() -> None:
    """Run the reviewed Agent-C protocol."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--approval", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    print(run(arguments.config, arguments.approval, arguments.output))


if __name__ == "__main__":
    main()
