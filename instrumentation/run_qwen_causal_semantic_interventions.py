"""Execute the prospective QCI-2 decision-semantic intervention campaign."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import sys
import time
import traceback
from typing import Any

import psutil
import torch

from causal.qci2_execution import assess_semantic_candidate, semantic_donor_mappings
from causal.qci_execution import QueryLedger, parse_candidate
from experiments.manifest import sha256_file
from instrumentation.adapters import Qwen2ModelAdapter
from instrumentation import run_qwen_causal_interventions as qci1
from paired_trace.metrics import validate_label_tokens
from paired_trace.run_model_qualification import (
    _cgroup_memory, _environment_inventory, _validate_model_candidate,
    _verify_snapshot_manifest, measure_hardware,
)


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "configs/causal_candidates/qwen_1_5b_qci2_semantic_v1.json"
SELECTION_PATH = ROOT / "results/phase1/candidate_selection/qwen15b_qci1/selection.json"
QUALIFICATION_ROWS_PATH = ROOT / "results/phase1/model_qualification/qwen15b_kaggle_20261110/mq_g1_rows.json"
QCI1_EVIDENCE = ROOT / "results/phase1/causal_interventions/qwen15b_qci1"
OUTPUT_DEFAULT = ROOT / "results/phase1/causal_interventions/qwen15b_qci2_discovery"
EXPERIMENT_ID = "P0_cross_20261112_qwen15b_qci2_semantic"
RUN_ID = f"{EXPERIMENT_ID}_seed42"


def _load_inputs() -> tuple[dict[str, Any], list[dict[str, Any]], list[Any]]:
    """Verify the prospective protocol, retained QCI-1 evidence and unchanged candidates."""
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    if protocol.get("status") != "prospectively_frozen_after_qci1_before_any_qci2_model_execution":
        raise ValueError("QCI-2 protocol is not prospectively frozen")
    qci1_report = qci1_verify()
    if qci1_report["next_gate"] != "STOP_NO_SUPPORTED_CANDIDATE":
        raise ValueError("QCI-2 requires the verified QCI-1 negative result")
    selection = json.loads(SELECTION_PATH.read_text(encoding="utf-8"))
    candidates = [parse_candidate(row) for row in selection["selected"]]
    if len(candidates) != 12 or protocol["candidate_policy"] != "reuse_all_12_qci1_candidates_without_reselection":
        raise ValueError("QCI-2 candidate reuse policy differs")
    rows = json.loads(QUALIFICATION_ROWS_PATH.read_text(encoding="utf-8"))
    by_id = {str(row["case_id"]): row for row in rows}
    discovery = [by_id[case_id] for case_id in protocol["discovery_case_ids"]]
    if any(row["split"] != "development" or not row["eligible"] for row in discovery):
        raise ValueError("QCI-2 includes an ineligible or non-development case")
    if set(protocol["development_audit_case_ids"]) & set(protocol["discovery_case_ids"]):
        raise ValueError("QCI-2 discovery and audit cases overlap")
    semantic_donor_mappings(discovery)
    expected = len(candidates) * len(discovery) * len(protocol["operators"])
    if expected != protocol["budget"]["candidate_executions"]:
        raise ValueError("QCI-2 candidate-execution budget differs")
    return protocol, discovery, candidates


def qci1_verify() -> dict[str, Any]:
    """Verify retained QCI-1 evidence before using it as follow-up provenance."""
    from scripts.verify_qci_bundle import verify

    return verify(QCI1_EVIDENCE)


def preflight(output_root: Path, cache_root: Path) -> dict[str, Any]:
    """Verify all QCI-2 inputs and CPU resources before model access."""
    output_root.mkdir(parents=True, exist_ok=True)
    cache_root.mkdir(parents=True, exist_ok=True)
    protocol, rows, candidates = _load_inputs()
    hardware = measure_hardware(cache_root)
    packages, environment_hash = _environment_inventory()
    result = {
        "schema_version": "aether.qci2-preflight.v1", "experiment_id": EXPERIMENT_ID,
        "run_id": RUN_ID, "utc_timestamp": datetime.now(timezone.utc).isoformat(),
        "git_commit": qci1._git("rev-parse", "HEAD"),
        "uncommitted_diff": bool(qci1._git("status", "--porcelain")),
        "model_id": protocol["model_id"], "model_revision": protocol["model_revision"],
        "tokenizer_revision": protocol["model_revision"], "random_seeds": [42],
        "python_version": platform.python_version(), "python_executable": sys.executable,
        "python_env_hash": environment_hash, "python_packages": packages,
        "command_line": sys.argv, "config_file": str(PROTOCOL_PATH.relative_to(ROOT)),
        "config_hash": sha256_file(PROTOCOL_PATH),
        "dataset_manifest_hashes": {
            "selection": sha256_file(SELECTION_PATH),
            "qualification_rows": sha256_file(QUALIFICATION_ROWS_PATH),
            "qci1_summary": sha256_file(QCI1_EVIDENCE / "summary.json"),
            "qci1_receipt": sha256_file(QCI1_EVIDENCE / "ingest_receipt.json"),
        },
        "discovery_case_ids": [row["case_id"] for row in rows],
        "candidate_ids": [f"{candidate.agent}.{candidate.candidate_id}" for candidate in candidates],
        "development_audit_executions": 0, "validation_executions": 0,
        "test_executions": 0, "model_accessed": False, "hardware": hardware,
        "decision": {"inputs_verified": True,
                     "hardware_pass": hardware["decision"]["overall"] == "PASS",
                     "overall": "PASS" if hardware["decision"]["overall"] == "PASS" else "BLOCKED"},
        "raw_output_path": str(output_root / "qci2_preflight.json"),
    }
    qci1._write_json(output_root / "qci2_preflight.json", result)
    return result


def run(output_root: Path, cache_root: Path) -> dict[str, Any]:
    """Run all frozen QCI-2 discovery interventions with one model load."""
    started = time.perf_counter()
    protocol, rows, candidates = _load_inputs()
    preflight_path = output_root / "qci2_preflight.json"
    marker_path = output_root / "qci2_model_access.json"
    if not preflight_path.is_file() or not marker_path.is_file():
        raise RuntimeError("run QCI-2 preflight and snapshot access first")
    preflight_record = json.loads(preflight_path.read_text(encoding="utf-8"))
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    if preflight_record["decision"]["overall"] != "PASS":
        raise RuntimeError("QCI-2 preflight did not pass")
    if marker.get("preflight_sha256") != sha256_file(preflight_path) or marker.get("state") != "MODEL_FILES_READY":
        raise RuntimeError("QCI-2 model-access marker is invalid")
    snapshot_path = Path(marker["snapshot_manifest_path"])
    if sha256_file(snapshot_path) != marker["snapshot_manifest_sha256"]:
        raise RuntimeError("QCI-2 snapshot manifest differs from marker")
    _verify_snapshot_manifest(json.loads(snapshot_path.read_text(encoding="utf-8")), cache_root)
    if torch.version.cuda is not None or torch.cuda.is_available():
        raise RuntimeError("QCI-2 preserves the qualified CPU-only condition")
    torch.manual_seed(42)
    torch.set_num_threads(2)
    model = _validate_model_candidate(protocol["model_id"])
    adapter = Qwen2ModelAdapter(
        model["model_id"], model["revision"], cache_root, dtype=torch.float32,
        device="cpu", local_files_only=True, low_cpu_mem_usage=True,
    )
    adapter.load()
    adapter.tokenizer.padding_side = "left"
    available = psutil.virtual_memory().available / 2**30
    _limit, cgroup_available = _cgroup_memory()
    if min(value for value in (available, cgroup_available) if value is not None) < 2.0:
        raise MemoryError("post-load memory is below QCI-2 minimum")
    label_ids = validate_label_tokens(adapter.tokenizer)
    donor_maps = semantic_donor_mappings(rows)
    sources: dict[tuple[str, str, str], dict[str, torch.Tensor]] = {}
    capture_steps = 0
    for index, row in enumerate(rows, start=1):
        print(f"QCI-2 source capture [{index}/{len(rows)}] {row['case_id']}", flush=True)
        for agent in ("sender", "receiver"):
            selected = [candidate for candidate in candidates if candidate.agent == agent]
            for condition in ("clean", "attacked"):
                prompt, ids = qci1._prompt_and_ids(row, agent, condition)
                inputs = qci1._qualified_inputs(adapter, prompt, ids)
                sources[(row["case_id"], agent, condition)] = qci1._capture_sources(adapter, inputs, selected)
                capture_steps += 1
    ledger = QueryLedger(
        int(protocol["budget"]["maximum_total_executions"]),
        int(protocol["budget"]["maximum_total_model_forward_steps"]),
        forward_steps=capture_steps,
    )
    raw_path = output_root / "raw_interventions.jsonl"
    output_root.mkdir(parents=True, exist_ok=True)
    all_results: list[dict[str, Any]] = []
    operators = list(protocol["operators"])
    with raw_path.open("w", encoding="utf-8") as stream:
        total = len(candidates) * len(rows) * len(operators)
        completed = 0
        for candidate in candidates:
            for row in rows:
                for operator in operators:
                    result = qci1._run_one(
                        adapter, candidate, row, operator, sources,
                        donor_maps["same_decision"], {item["case_id"]: item for item in rows},
                        label_ids,
                        {"irrelevant_token_position": 1, "sender_generation_max_new_tokens": 4,
                         "identity_tolerance": {"absolute": 1e-6, "relative": 1e-5}},
                        ledger, semantic_donor_maps=donor_maps,
                    )
                    all_results.append(result)
                    stream.write(json.dumps(result, sort_keys=True, allow_nan=False) + "\n")
                    stream.flush()
                    completed += 1
                    print(f"QCI-2 [{completed}/{total}] {candidate.candidate_id} {row['case_id']} {operator} status={result['status']}", flush=True)
    message_controls = qci1._run_message_controls(adapter, rows, label_ids, ledger)
    assessments = [
        assess_semantic_candidate(
            [row for row in all_results if row["candidate_id"] == f"{candidate.agent}.{candidate.candidate_id}"],
            protocol["support_thresholds"],
        ) for candidate in candidates
    ]
    supported = [row["candidate_id"] for row in assessments if row["status"] == "supported"]
    summary = {
        "schema_version": "aether.qci2-discovery.v1", "experiment_id": EXPERIMENT_ID,
        "run_id": RUN_ID, "utc_timestamp": datetime.now(timezone.utc).isoformat(),
        "model_id": protocol["model_id"], "model_revision": protocol["model_revision"],
        "protocol_hash": sha256_file(PROTOCOL_PATH), "selection_hash": sha256_file(SELECTION_PATH),
        "qci1_summary_hash": sha256_file(QCI1_EVIDENCE / "summary.json"),
        "discovery_case_ids": [row["case_id"] for row in rows],
        "development_audit_executions": 0, "validation_executions": 0, "test_executions": 0,
        "candidate_count": len(candidates), "candidate_execution_count": len(all_results),
        "message_positive_control_count": len(message_controls),
        "invalid_or_error_count": sum(row["status"] != "ok" for row in all_results),
        "supported_candidates": supported,
        "assessment_outcome": "supported_candidates_found" if supported else "no_semantic_candidate_passed",
        "query_ledger": asdict(ledger), "runtime_seconds": time.perf_counter() - started,
        "next_state": "READY_FOR_QCI2_DEVELOPMENT_AUDIT" if supported else "STOP_DECISION_SEMANTIC_CLAIM",
        "claim_boundary": protocol["claim_boundary"],
    }
    message_path = output_root / "message_positive_controls.json"
    assessments_path = output_root / "candidate_assessments.json"
    summary_path = output_root / "summary.json"
    qci1._write_json(message_path, message_controls)
    qci1._write_json(assessments_path, assessments)
    qci1._write_json(summary_path, summary)
    marker["state"] = "QCI2_DISCOVERY_COMPLETE"
    marker["utc_timestamp"] = summary["utc_timestamp"]
    qci1._write_json(marker_path, marker)
    packages, environment_hash = _environment_inventory()
    manifest = {
        "manifest_version": "1.0.0", "experiment_id": EXPERIMENT_ID, "run_id": RUN_ID,
        "utc_timestamp": summary["utc_timestamp"], "git_commit": qci1._git("rev-parse", "HEAD"),
        "uncommitted_diff": bool(qci1._git("status", "--porcelain")),
        "dataset_manifest_hashes": {
            "selection": sha256_file(SELECTION_PATH), "qualification_rows": sha256_file(QUALIFICATION_ROWS_PATH),
            "qci1_summary": sha256_file(QCI1_EVIDENCE / "summary.json"),
        },
        "model_id": protocol["model_id"], "model_revision": protocol["model_revision"],
        "tokenizer_revision": protocol["model_revision"], "prompt_versions": {"qualification": "V2.1"},
        "random_seeds": [42], "hardware": platform.platform(), "python_env_hash": environment_hash,
        "python_packages": packages, "command_line": sys.argv,
        "config_file": str(PROTOCOL_PATH.relative_to(ROOT)), "raw_output_path": str(raw_path),
        "artifact_paths": {str(path): sha256_file(path) for path in (
            raw_path, message_path, assessments_path, summary_path, preflight_path, marker_path, snapshot_path
        )},
    }
    qci1._write_json(output_root / "manifest.json", manifest)
    return summary


def main() -> None:
    """Run QCI-2 preflight or the complete discovery campaign."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT_DEFAULT)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--preflight-only", action="store_true")
    arguments = parser.parse_args()
    try:
        result = preflight(arguments.output.resolve(), arguments.cache.resolve()) if arguments.preflight_only else run(arguments.output.resolve(), arguments.cache.resolve())
        print(json.dumps(result, indent=2, sort_keys=True))
    except Exception as error:
        arguments.output.mkdir(parents=True, exist_ok=True)
        failure = {
            "schema_version": "aether.qci2-failure.v1", "experiment_id": EXPERIMENT_ID,
            "run_id": RUN_ID, "utc_timestamp": datetime.now(timezone.utc).isoformat(),
            "exception_type": type(error).__name__, "message": str(error),
            "traceback": traceback.format_exc(), "git_commit": qci1._git("rev-parse", "HEAD"),
            "uncommitted_diff": bool(qci1._git("status", "--porcelain")),
            "model_id": json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))["model_id"],
            "model_revision": json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))["model_revision"],
            "random_seeds": [42], "config_file": str(PROTOCOL_PATH.relative_to(ROOT)),
            "config_hash": sha256_file(PROTOCOL_PATH), "validation_executions": 0, "test_executions": 0,
        }
        failure_path = arguments.output / "execution_failure.json"
        qci1._write_json(failure_path, failure)
        packages, environment_hash = _environment_inventory()
        qci1._write_json(arguments.output / "failure_manifest.json", {
            "manifest_version": "1.0.0", "experiment_id": EXPERIMENT_ID,
            "run_id": RUN_ID, "utc_timestamp": failure["utc_timestamp"],
            "git_commit": failure["git_commit"], "uncommitted_diff": failure["uncommitted_diff"],
            "dataset_manifest_hashes": {
                "selection": sha256_file(SELECTION_PATH),
                "qualification_rows": sha256_file(QUALIFICATION_ROWS_PATH),
                "qci1_summary": sha256_file(QCI1_EVIDENCE / "summary.json"),
            },
            "model_id": failure["model_id"], "model_revision": failure["model_revision"],
            "tokenizer_revision": failure["model_revision"], "prompt_versions": {"qualification": "V2.1"},
            "random_seeds": [42], "hardware": platform.platform(),
            "python_env_hash": environment_hash, "python_packages": packages,
            "command_line": sys.argv, "config_file": failure["config_file"],
            "raw_output_path": str(failure_path),
            "artifact_paths": {str(failure_path): sha256_file(failure_path)},
        })
        raise


if __name__ == "__main__":
    main()
