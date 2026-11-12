"""Execute the prospectively frozen QCI-2A1 semantic development audit."""

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

from causal.qci_audit import build_audit_plan
from causal.qci2_execution import assess_semantic_candidate, semantic_donor_mappings
from causal.qci_execution import QueryLedger, parse_candidate
from experiments.manifest import sha256_file
from instrumentation.adapters import Qwen2ModelAdapter
from instrumentation import run_qwen_causal_interventions as qci1
from instrumentation.run_qwen_causal_semantic_interventions import QUALIFICATION_ROWS_PATH
from paired_trace.metrics import validate_label_tokens
from paired_trace.run_model_qualification import (
    _cgroup_memory, _environment_inventory, _validate_model_candidate,
    _verify_snapshot_manifest, measure_hardware,
)
from scripts.verify_qci2_bundle import verify


ROOT = Path(__file__).resolve().parents[1]
BASE_PROTOCOL_PATH = ROOT / "configs/causal_candidates/qwen_1_5b_qci2_semantic_v1.json"
AUDIT_PROTOCOL_PATH = ROOT / "configs/causal_candidates/qwen_1_5b_qci2_development_audit_v1.json"
SELECTION_PATH = ROOT / "results/phase1/candidate_selection/qwen15b_qci1/selection.json"
OUTPUT_DEFAULT = ROOT / "results/phase1/causal_interventions/qwen15b_qci2_audit"
EXPERIMENT_ID = "P0_cross_20261112_qwen15b_qci2_semantic_audit"
RUN_ID = f"{EXPERIMENT_ID}_seed42"


def _load_inputs(discovery_root: Path) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], list[Any], dict[str, Any]]:
    """Verify QCI-2 evidence and construct the immutable audit plan."""
    verification = verify(discovery_root)
    base = json.loads(BASE_PROTOCOL_PATH.read_text(encoding="utf-8"))
    protocol = json.loads(AUDIT_PROTOCOL_PATH.read_text(encoding="utf-8"))
    if protocol.get("status") != "prospectively_frozen_before_qci2_discovery_result":
        raise ValueError("QCI-2 audit protocol is not prospectively frozen")
    if (protocol["model_id"], protocol["model_revision"]) != (base["model_id"], base["model_revision"]):
        raise ValueError("QCI-2 audit model differs from discovery")
    selection = json.loads(SELECTION_PATH.read_text(encoding="utf-8"))
    qualification = json.loads(QUALIFICATION_ROWS_PATH.read_text(encoding="utf-8"))
    plan = build_audit_plan(verification, selection, qualification, protocol)
    candidates = [parse_candidate(row) for row in plan["candidate_rows"]]
    by_id = {str(row["case_id"]): row for row in qualification}
    rows = [by_id[case_id] for case_id in plan["case_ids"]]
    semantic_donor_mappings(rows)
    return base, protocol, rows, candidates, plan


def _completed(output: Path) -> int:
    """Count retained executions after an interrupted audit."""
    raw = output / "raw_audit_interventions.jsonl"
    candidate_count = sum(bool(line.strip()) for line in raw.read_text(encoding="utf-8").splitlines()) if raw.is_file() else 0
    controls = output / "message_positive_controls.json"
    control_count = len(json.loads(controls.read_text(encoding="utf-8"))) if controls.is_file() else 0
    return candidate_count + control_count


def preflight(output: Path, cache: Path, discovery: Path) -> dict[str, Any]:
    """Verify discovery authorization, audit inputs and hardware before access."""
    output.mkdir(parents=True, exist_ok=True)
    cache.mkdir(parents=True, exist_ok=True)
    base, _protocol, rows, candidates, plan = _load_inputs(discovery)
    hardware = measure_hardware(cache)
    packages, environment_hash = _environment_inventory()
    result = {
        "schema_version": "aether.qci2-audit-preflight.v1", "experiment_id": EXPERIMENT_ID,
        "run_id": RUN_ID, "utc_timestamp": datetime.now(timezone.utc).isoformat(),
        "git_commit": qci1._git("rev-parse", "HEAD"),
        "uncommitted_diff": bool(qci1._git("status", "--porcelain")),
        "model_id": base["model_id"], "model_revision": base["model_revision"],
        "tokenizer_revision": base["model_revision"], "random_seeds": [42],
        "python_version": platform.python_version(), "python_executable": sys.executable,
        "python_env_hash": environment_hash, "python_packages": packages,
        "command_line": sys.argv, "config_file": str(AUDIT_PROTOCOL_PATH.relative_to(ROOT)),
        "config_hash": sha256_file(AUDIT_PROTOCOL_PATH),
        "dataset_manifest_hashes": {
            "selection": sha256_file(SELECTION_PATH), "qualification_rows": sha256_file(QUALIFICATION_ROWS_PATH),
            "discovery_summary": sha256_file(discovery / "summary.json"),
            "discovery_manifest": sha256_file(discovery / "manifest.json"),
        },
        "development_audit_case_ids": [row["case_id"] for row in rows],
        "candidate_ids": [f"{item.agent}.{item.candidate_id}" for item in candidates],
        "audit_plan": plan, "development_audit_executions": 0,
        "validation_executions": 0, "test_executions": 0, "model_accessed": False,
        "hardware": hardware,
        "decision": {"inputs_verified": True, "hardware_pass": hardware["decision"]["overall"] == "PASS",
                     "overall": "PASS" if hardware["decision"]["overall"] == "PASS" else "BLOCKED"},
        "raw_output_path": str(output / "audit_preflight.json"),
    }
    qci1._write_json(output / "audit_preflight.json", result)
    return result


def run(output: Path, cache: Path, discovery: Path) -> dict[str, Any]:
    """Run the authorized four-case semantic audit with one model load."""
    started = time.perf_counter()
    base, protocol, rows, candidates, plan = _load_inputs(discovery)
    preflight_path, marker_path = output / "audit_preflight.json", output / "audit_model_access.json"
    if not preflight_path.is_file() or not marker_path.is_file():
        raise RuntimeError("run QCI-2 audit preflight and snapshot access first")
    preflight_record = json.loads(preflight_path.read_text(encoding="utf-8"))
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    if preflight_record["decision"]["overall"] != "PASS":
        raise RuntimeError("QCI-2 audit preflight did not pass")
    if marker.get("state") != "MODEL_FILES_READY" or marker.get("preflight_sha256") != sha256_file(preflight_path):
        raise RuntimeError("QCI-2 audit model marker is invalid")
    snapshot_path = Path(marker["snapshot_manifest_path"])
    if sha256_file(snapshot_path) != marker["snapshot_manifest_sha256"]:
        raise RuntimeError("QCI-2 audit snapshot manifest differs")
    _verify_snapshot_manifest(json.loads(snapshot_path.read_text(encoding="utf-8")), cache)
    if torch.version.cuda is not None or torch.cuda.is_available():
        raise RuntimeError("QCI-2A1 preserves the qualified CPU-only condition")
    torch.manual_seed(42); torch.set_num_threads(2)
    model = _validate_model_candidate(base["model_id"])
    adapter = Qwen2ModelAdapter(model["model_id"], model["revision"], cache, dtype=torch.float32,
                                device="cpu", local_files_only=True, low_cpu_mem_usage=True)
    adapter.load(); adapter.tokenizer.padding_side = "left"
    available = psutil.virtual_memory().available / 2**30
    _limit, cgroup_available = _cgroup_memory()
    if min(value for value in (available, cgroup_available) if value is not None) < 2.0:
        raise MemoryError("post-load memory is below QCI-2 audit minimum")
    label_ids = validate_label_tokens(adapter.tokenizer)
    donor_maps = semantic_donor_mappings(rows)
    sources: dict[tuple[str, str, str], dict[str, torch.Tensor]] = {}
    capture_steps = 0
    for row in rows:
        for agent in ("sender", "receiver"):
            selected = [candidate for candidate in candidates if candidate.agent == agent]
            for condition in ("clean", "attacked"):
                prompt, ids = qci1._prompt_and_ids(row, agent, condition)
                sources[(row["case_id"], agent, condition)] = qci1._capture_sources(
                    adapter, qci1._qualified_inputs(adapter, prompt, ids), selected)
                capture_steps += 1
    budget = protocol["budget"]
    ledger = QueryLedger(int(budget["maximum_total_executions"]),
                         int(budget["maximum_total_model_forward_steps"]), forward_steps=capture_steps)
    raw_path = output / "raw_audit_interventions.jsonl"
    results: list[dict[str, Any]] = []
    with raw_path.open("w", encoding="utf-8") as stream:
        for candidate in candidates:
            for row in rows:
                for operator in protocol["operators_per_candidate_per_case"]:
                    result = qci1._run_one(
                        adapter, candidate, row, operator, sources, donor_maps["same_decision"],
                        {item["case_id"]: item for item in rows}, label_ids, protocol["execution"], ledger,
                        semantic_donor_maps=donor_maps,
                    )
                    results.append(result)
                    stream.write(json.dumps(result, sort_keys=True, allow_nan=False) + "\n"); stream.flush()
    controls = qci1._run_message_controls(adapter, rows, label_ids, ledger)
    assessments = [assess_semantic_candidate(
        [row for row in results if row["candidate_id"] == f"{candidate.agent}.{candidate.candidate_id}"],
        base["support_thresholds"], expected_count=4,
    ) for candidate in candidates]
    supported = [row["candidate_id"] for row in assessments if row["status"] == "supported"]
    summary = {
        "schema_version": "aether.qci2-audit.v1", "experiment_id": EXPERIMENT_ID, "run_id": RUN_ID,
        "utc_timestamp": datetime.now(timezone.utc).isoformat(), "model_id": base["model_id"],
        "model_revision": base["model_revision"], "protocol_hash": sha256_file(AUDIT_PROTOCOL_PATH),
        "discovery_summary_hash": sha256_file(discovery / "summary.json"),
        "development_audit_case_ids": [row["case_id"] for row in rows],
        "candidate_ids": plan["candidate_ids"], "excluded_supported_candidates": plan["excluded_supported_candidates"],
        "audit_supported_candidates": supported, "candidate_execution_count": len(results),
        "message_positive_control_count": len(controls),
        "development_audit_executions": len(results) + len(controls),
        "invalid_or_error_count": sum(row["status"] != "ok" for row in results),
        "validation_executions": 0, "test_executions": 0, "query_ledger": asdict(ledger),
        "runtime_seconds": time.perf_counter() - started,
        "next_state": protocol["next_state_if_supported"] if supported else protocol["next_state_if_rejected"],
        "claim_boundary": protocol["claim_boundary"],
    }
    controls_path, assessments_path, summary_path = output / "message_positive_controls.json", output / "candidate_audit_assessments.json", output / "summary.json"
    qci1._write_json(controls_path, controls); qci1._write_json(assessments_path, assessments); qci1._write_json(summary_path, summary)
    marker.update({"state": "QCI2_AUDIT_COMPLETE", "utc_timestamp": summary["utc_timestamp"]}); qci1._write_json(marker_path, marker)
    packages, environment_hash = _environment_inventory()
    qci1._write_json(output / "manifest.json", {
        "manifest_version": "1.0.0", "experiment_id": EXPERIMENT_ID, "run_id": RUN_ID,
        "utc_timestamp": summary["utc_timestamp"], "git_commit": qci1._git("rev-parse", "HEAD"),
        "uncommitted_diff": bool(qci1._git("status", "--porcelain")),
        "dataset_manifest_hashes": preflight_record["dataset_manifest_hashes"],
        "model_id": base["model_id"], "model_revision": base["model_revision"],
        "tokenizer_revision": base["model_revision"], "prompt_versions": {"qualification": "V2.1"},
        "random_seeds": [42], "hardware": platform.platform(), "python_env_hash": environment_hash,
        "python_packages": packages, "command_line": sys.argv,
        "config_file": str(AUDIT_PROTOCOL_PATH.relative_to(ROOT)), "raw_output_path": str(raw_path),
        "artifact_paths": {str(path): sha256_file(path) for path in (
            raw_path, controls_path, assessments_path, summary_path, preflight_path, marker_path, snapshot_path)},
    })
    return summary


def main() -> None:
    """Run QCI-2A1 preflight or the authorized semantic audit."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--discovery", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=OUTPUT_DEFAULT)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    try:
        result = preflight(args.output.resolve(), args.cache.resolve(), args.discovery.resolve()) if args.preflight_only else run(args.output.resolve(), args.cache.resolve(), args.discovery.resolve())
        print(json.dumps(result, indent=2, sort_keys=True))
    except Exception as error:
        args.output.mkdir(parents=True, exist_ok=True)
        failure = {
            "schema_version": "aether.qci2-audit-failure.v1", "experiment_id": EXPERIMENT_ID,
            "run_id": RUN_ID, "utc_timestamp": datetime.now(timezone.utc).isoformat(),
            "exception_type": type(error).__name__, "message": str(error), "traceback": traceback.format_exc(),
            "git_commit": qci1._git("rev-parse", "HEAD"),
            "uncommitted_diff": bool(qci1._git("status", "--porcelain")),
            "model_id": json.loads(BASE_PROTOCOL_PATH.read_text())["model_id"],
            "model_revision": json.loads(BASE_PROTOCOL_PATH.read_text())["model_revision"],
            "random_seeds": [42], "config_file": str(AUDIT_PROTOCOL_PATH.relative_to(ROOT)),
            "config_hash": sha256_file(AUDIT_PROTOCOL_PATH), "development_audit_executions": _completed(args.output),
            "validation_executions": 0, "test_executions": 0,
        }
        qci1._write_json(args.output / "execution_failure.json", failure)
        raise


if __name__ == "__main__":
    main()
