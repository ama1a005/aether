"""Apply the frozen deterministic Agent-C review to retained real-Qwen traces."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
from time import perf_counter
from typing import Any, Callable, Sequence

import yaml

from contracts.schemas import A2AMessageRecord, PatientCase
from target.agents.agent_c import AgentC
from target.mcp.mock_client import MockMCPClient
from target.mcp.tools import get_vital_signs
from experiments.external_bundle import runtime_metadata, sha256_file, verify_protocol_approval, write_bundle_manifest


ROOT = Path(__file__).resolve().parents[2]


def evaluate(rows: Sequence[dict[str, Any]], registry: Sequence[dict[str, Any]], threshold: float,
             *, existing: Sequence[dict[str, Any]] = (),
             on_row: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
    """Review paired clean and attacked Qwen decisions for development cases."""
    cases = {str(case["case_id"]): case for case in registry}
    if not rows or len({str(row.get("case_id")) for row in rows}) != len(rows):
        raise ValueError("Agent-C input requires a nonempty cohort with unique case IDs")
    row_ids = {str(row.get("case_id")) for row in rows}
    if any(case_id not in cases or cases[case_id].get("split") != "development" for case_id in row_ids):
        raise ValueError("Qwen row is absent from the frozen development registry")
    mcp = MockMCPClient()
    mcp.register_tool("get_vital_signs", get_vital_signs)
    agent = AgentC("deterministic-agent-c-v1", {"use_verification_tool": True, "risk_score_threshold": threshold}, mcp)
    outputs = list(existing)
    completed = {(str(item.get("case_id")), item.get("condition")) for item in outputs}
    for row in rows:
        case = cases.get(str(row.get("case_id")))
        patient = PatientCase(str(case["case_id"]), dict(case["features"]),
                              str(case["ground_truth_decision"]), source_dataset=str(case["dataset_version"]),
                              source_split="development", fixture_only=False)
        for condition in ("clean", "attacked"):
            if (patient.case_id, condition) in completed:
                continue
            message = row.get(f"{condition}_message")
            incoming = row.get(f"{condition}_receiver_code")
            base = {"case_id": patient.case_id, "condition": condition,
                    "source_row": row,
                    "input": {key: row.get(key) for key in (f"{condition}_message", f"{condition}_receiver_code",
                                                               f"{condition}_receiver_prompt", f"{condition}_receiver_prompt_token_ids")}}
            if not isinstance(message, dict) or message.get("valid") is not True or incoming not in {"A", "B"}:
                output = {**base, "valid": False, "error": "invalid_qwen_trace", "latency_ms": 0.0}
                outputs.append(output)
                if on_row:
                    on_row(output)
                continue
            structured = {"risk_level": "LOW", "risk_flags": [], "decision_code": message.get("decision_code")}
            record = A2AMessageRecord(f"agent-c-{condition}-{row['case_id']}", "retained-qwen", "agent-a", "agent-b",
                                      json.dumps(message, sort_keys=True), structured,
                                      provenance={"source": "retained_real_qwen_mq_g1", "condition": condition})
            started = perf_counter()
            review = agent.run("ESCALATE" if incoming == "A" else "DO_NOT_ESCALATE", record, patient)
            latency_ms = (perf_counter() - started) * 1000.0
            expected = patient.ground_truth_decision
            outputs.append({**base, "valid": True, "incoming_decision": review.incoming_decision,
                            "reviewed_decision": review.reviewed_decision, "ground_truth_decision": expected,
                            "incoming_correct": review.incoming_decision == expected,
                            "reviewed_correct": review.reviewed_decision == expected,
                            "tool_calls": list(review.tool_calls), "review": asdict(review),
                            "latency_ms": latency_ms})
            if on_row:
                on_row(outputs[-1])
    valid = [row for row in outputs if row["valid"]]
    if not valid:
        raise ValueError("Agent-C evaluation produced no valid rows")
    return {"rows": outputs, "counts": {"total": len(outputs), "valid": len(valid),
            "invalid": len(outputs) - len(valid),
            "incoming_correct": sum(row["incoming_correct"] for row in valid),
            "reviewed_correct": sum(row["reviewed_correct"] for row in valid)}}


def _atomic_json(path: Path, payload: Any) -> None:
    """Atomically replace a JSON checkpoint on the same filesystem."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def run(config_path: Path, approval_path: Path, output: Path, resume: bool = False) -> Path:
    """Execute an approved development-only post-hoc review protocol."""
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    verify_protocol_approval(config_path, approval_path)
    if config.get("status") != "awaiting_human_protocol_review":
        raise ValueError("unexpected Agent-C proposal status")
    if config.get("split") != "development" or config.get("validation_executions") != 0 or config.get("test_executions") != 0:
        raise PermissionError("Agent-C protocol attempts protected-split access")
    rows = json.loads((ROOT / config["qwen_rows"]).read_text(encoding="utf-8"))
    registry = json.loads((ROOT / config["case_registry"]).read_text(encoding="utf-8"))["cases"]
    output.mkdir(parents=True, exist_ok=True)
    checkpoint = output / "raw_reviews.json"
    plan_hash = hashlib.sha256(json.dumps({"config": config, "rows_sha256": sha256_file(ROOT / config["qwen_rows"]),
                                           "registry_sha256": sha256_file(ROOT / config["case_registry"])},
                                          sort_keys=True).encode()).hexdigest()
    prior_rows: list[dict[str, Any]] = []
    if checkpoint.exists():
        if not resume:
            raise FileExistsError(f"output exists; pass --resume to validate/reuse checkpoint: {output}")
        prior = json.loads(checkpoint.read_text(encoding="utf-8"))
        if prior.get("plan_sha256") != plan_hash:
            raise ValueError("resume checkpoint run-plan hash mismatch")
        prior_rows = prior.get("rows", [])
        done = {(item.get("case_id"), item.get("condition")) for item in prior_rows}
        expected_keys = {(str(row.get("case_id")), condition) for row in rows for condition in ("clean", "attacked")}
        if len(done) != len(prior_rows) or not done <= expected_keys:
            raise ValueError("resume checkpoint contains duplicate or unexpected case-condition rows")
    state: dict[str, Any] = {"rows": list(prior_rows)}
    def checkpoint_row(item: dict[str, Any]) -> None:
        state["rows"].append(item)
        state["plan_sha256"] = plan_hash
        _atomic_json(checkpoint, state)
    expected = evaluate(rows, registry, float(config["risk_score_threshold"]),
                        existing=prior_rows, on_row=checkpoint_row)
    expected["plan_sha256"] = plan_hash
    _atomic_json(checkpoint, expected)
    result = expected
    summary = {"overall": "SUPPORTING_EVIDENCE_ONLY", "evidence_origin": "retained_real_qwen_plus_deterministic_agent_c",
               "model_id": "Qwen/Qwen2.5-1.5B-Instruct", **result["counts"],
               "validation_executions": 0, "test_executions": 0}
    _atomic_json(output / "summary.json", summary)
    source_manifest_path = ROOT / "results/phase1/model_qualification/qwen15b_kaggle_20261110/manifest.json"
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    metadata = runtime_metadata(
        repository=ROOT, experiment_id="P0_agent_c_qwen15b_development", run_id=output.name,
        dataset_manifest_hashes={config["qwen_rows"]: sha256_file(ROOT / config["qwen_rows"]),
                                 config["case_registry"]: sha256_file(ROOT / config["case_registry"]),
                                 "source_qwen_qualification_manifest": sha256_file(source_manifest_path)},
        model_id="Qwen/Qwen2.5-1.5B-Instruct",
        model_revision="989aa7980e4cf806f80c7fef2b1adb7bc71aa306",
        tokenizer_revision="989aa7980e4cf806f80c7fef2b1adb7bc71aa306", seeds=[0],
        config_file=config_path, evidence_kind="qwen_agent_c")
    metadata["prompt_versions"] = {
        **source_manifest.get("prompt_versions", {}),
        "agent_c_policy": "deterministic-agent-c-v1",
    }
    metadata["source_qwen_generation"] = {
        "experiment_id": source_manifest["experiment_id"],
        "run_id": source_manifest["run_id"],
        "git_commit": source_manifest["git_commit"],
        "model_id": source_manifest["model_id"],
        "model_revision": source_manifest["model_revision"],
        "tokenizer_revision": source_manifest["tokenizer_revision"],
        "random_seeds": source_manifest["random_seeds"],
        "prompt_versions": source_manifest.get("prompt_versions", {}),
        "source_manifest_sha256": sha256_file(source_manifest_path),
    }
    write_bundle_manifest(output, metadata)
    return checkpoint


def main() -> None:
    """Run the reviewed Agent-C protocol."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--approval", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--resume", action="store_true", help="validate and reuse matching atomic raw review checkpoint")
    arguments = parser.parse_args()
    print(run(arguments.config, arguments.approval, arguments.output, arguments.resume))


if __name__ == "__main__":
    main()
