"""Execute the prospectively frozen QCI-A1 development-only audit."""

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
from causal.qci_execution import QueryLedger, assess_candidate, parse_candidate, shuffled_donor_mapping
from experiments.manifest import sha256_file
from instrumentation.adapters import Qwen2ModelAdapter
from instrumentation.run_qwen_causal_interventions import (
    ROOT, BASE_PROTOCOL_PATH, QUALIFICATION_ROWS_PATH,
    _capture_sources, _environment_inventory, _git, _cgroup_memory,
    _prompt_and_ids, _qualified_inputs, _run_message_controls, _run_one,
    _validate_model_candidate, _verify_snapshot_manifest, _write_json,
    measure_hardware, validate_label_tokens,
)
from scripts.verify_qci_bundle import verify


SELECTION_PATH = ROOT / "results/phase1/candidate_selection/qwen15b_qci1/selection.json"
AUDIT_PROTOCOL_PATH = ROOT / "configs/causal_candidates/qwen_1_5b_qci1_development_audit_v1.json"
OUTPUT_DEFAULT = ROOT / "results/phase1/causal_interventions/qwen15b_qci1_audit"
EXPERIMENT_ID = "P0_cross_20261111_qwen15b_qci1_audit"
RUN_ID = f"{EXPERIMENT_ID}_seed42"


def _load_audit_inputs(
    discovery_root: Path,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], list[Any], dict[str, Any]]:
    """Verify discovery evidence and construct the immutable audit inputs."""
    verification = verify(discovery_root)
    base = json.loads(BASE_PROTOCOL_PATH.read_text(encoding="utf-8"))
    protocol = json.loads(AUDIT_PROTOCOL_PATH.read_text(encoding="utf-8"))
    if protocol.get("status") != "prospectively_frozen_before_qci_discovery_results_are_ingested":
        raise ValueError("QCI audit protocol is not prospectively frozen")
    if protocol["model_id"] != base["model_id"] or protocol["model_revision"] != base["model_revision"]:
        raise ValueError("QCI audit model differs from the frozen intervention model")
    selection = json.loads(SELECTION_PATH.read_text(encoding="utf-8"))
    qualification_rows = json.loads(QUALIFICATION_ROWS_PATH.read_text(encoding="utf-8"))
    plan = build_audit_plan(verification, selection, qualification_rows, protocol)
    candidates = [parse_candidate(row) for row in plan["candidate_rows"]]
    by_id = {str(row["case_id"]): row for row in qualification_rows}
    rows = [by_id[case_id] for case_id in plan["case_ids"]]
    return base, protocol, rows, candidates, plan


def _completed_audit_executions(output_root: Path) -> int:
    """Count retained candidate and message executions after a failed attempt."""
    raw_path = output_root / "raw_audit_interventions.jsonl"
    candidate_count = 0
    if raw_path.is_file():
        candidate_count = sum(
            1 for line in raw_path.read_text(encoding="utf-8").splitlines() if line.strip()
        )
    controls_path = output_root / "message_positive_controls.json"
    control_count = 0
    if controls_path.is_file():
        controls = json.loads(controls_path.read_text(encoding="utf-8"))
        if not isinstance(controls, list):
            raise ValueError("QCI audit message controls are not a list")
        control_count = len(controls)
    return candidate_count + control_count


def preflight(output_root: Path, cache_root: Path, discovery_root: Path) -> dict[str, Any]:
    """Verify the supported discovery bundle, audit plan and hardware pre-access."""
    base, protocol, rows, candidates, plan = _load_audit_inputs(discovery_root)
    hardware = measure_hardware(cache_root)
    packages, environment_hash = _environment_inventory()
    result = {
        "schema_version": "aether.qci-audit-preflight.v1",
        "experiment_id": EXPERIMENT_ID,
        "run_id": RUN_ID,
        "utc_timestamp": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git("rev-parse", "HEAD"),
        "uncommitted_diff": bool(_git("diff", "--name-only")),
        "model_id": base["model_id"],
        "model_revision": base["model_revision"],
        "tokenizer_revision": base["model_revision"],
        "random_seeds": [42],
        "python_version": platform.python_version(),
        "python_executable": sys.executable,
        "python_env_hash": environment_hash,
        "python_packages": packages,
        "command_line": sys.argv,
        "config_file": str(AUDIT_PROTOCOL_PATH.relative_to(ROOT)),
        "config_hash": sha256_file(AUDIT_PROTOCOL_PATH),
        "dataset_manifest_hashes": {
            "selection": sha256_file(SELECTION_PATH),
            "qualification_rows": sha256_file(QUALIFICATION_ROWS_PATH),
            "discovery_summary": sha256_file(discovery_root / "summary.json"),
            "discovery_manifest": sha256_file(discovery_root / "manifest.json"),
        },
        "development_audit_case_ids": [row["case_id"] for row in rows],
        "candidate_ids": [f"{candidate.agent}.{candidate.candidate_id}" for candidate in candidates],
        "audit_plan": plan,
        "development_audit_executions": 0,
        "validation_executions": 0,
        "test_executions": 0,
        "model_accessed": False,
        "hardware": hardware,
        "decision": {
            "inputs_verified": True,
            "hardware_pass": hardware["decision"]["overall"] == "PASS",
            "overall": "PASS" if hardware["decision"]["overall"] == "PASS" else "BLOCKED",
        },
        "raw_output_path": str(output_root / "audit_preflight.json"),
    }
    _write_json(output_root / "audit_preflight.json", result)
    return result


def run(output_root: Path, cache_root: Path, discovery_root: Path) -> dict[str, Any]:
    """Run the frozen four-case audit for discovery-supported candidates only."""
    started = time.perf_counter()
    base, protocol, rows, candidates, plan = _load_audit_inputs(discovery_root)
    preflight_path = output_root / "audit_preflight.json"
    marker_path = output_root / "audit_model_access.json"
    if not preflight_path.is_file() or not marker_path.is_file():
        raise RuntimeError("run QCI audit preflight and snapshot access first")
    preflight_record = json.loads(preflight_path.read_text(encoding="utf-8"))
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    if preflight_record["decision"]["overall"] != "PASS":
        raise RuntimeError("QCI audit preflight did not pass")
    if marker.get("preflight_sha256") != sha256_file(preflight_path) or marker.get("state") != "MODEL_FILES_READY":
        raise RuntimeError("QCI audit model-access marker is invalid")
    snapshot_path = Path(marker["snapshot_manifest_path"])
    if sha256_file(snapshot_path) != marker["snapshot_manifest_sha256"]:
        raise RuntimeError("QCI audit snapshot manifest differs from marker")
    _verify_snapshot_manifest(json.loads(snapshot_path.read_text(encoding="utf-8")), cache_root)
    if torch.version.cuda is not None or torch.cuda.is_available():
        raise RuntimeError("QCI-A1 requires the qualified CPU-only condition")
    torch.manual_seed(42)
    torch.set_num_threads(2)
    model = _validate_model_candidate(base["model_id"])
    adapter = Qwen2ModelAdapter(
        model["model_id"], model["revision"], cache_root, dtype=torch.float32,
        device="cpu", local_files_only=True, low_cpu_mem_usage=True,
    )
    adapter.load()
    adapter.tokenizer.padding_side = "left"
    available = psutil.virtual_memory().available / 2**30
    _memory_limit, cgroup_available = _cgroup_memory()
    if min(value for value in (available, cgroup_available) if value is not None) < 2.0:
        raise MemoryError("post-load memory is below QCI audit minimum")
    label_ids = validate_label_tokens(adapter.tokenizer)
    by_id = {row["case_id"]: row for row in rows}
    donor_map = shuffled_donor_mapping(rows)
    sources: dict[tuple[str, str, str], dict[str, torch.Tensor]] = {}
    forward_steps = 0
    for row in rows:
        for agent in ("sender", "receiver"):
            selected = [candidate for candidate in candidates if candidate.agent == agent]
            for condition in ("clean", "attacked"):
                prompt, ids = _prompt_and_ids(row, agent, condition)
                sources[(row["case_id"], agent, condition)] = _capture_sources(
                    adapter, _qualified_inputs(adapter, prompt, ids), selected
                )
                forward_steps += 1
    budget = protocol["budget"]
    ledger = QueryLedger(
        int(budget["maximum_total_executions"]),
        int(budget["maximum_total_model_forward_steps"]),
        forward_steps=forward_steps,
    )
    execution = dict(protocol["execution"])
    operators = list(protocol["operators_per_candidate_per_case"])
    raw_path = output_root / "raw_audit_interventions.jsonl"
    all_results: list[dict[str, Any]] = []
    output_root.mkdir(parents=True, exist_ok=True)
    with raw_path.open("w", encoding="utf-8") as stream:
        for candidate in candidates:
            for row in rows:
                for operator in operators:
                    result = _run_one(
                        adapter, candidate, row, operator, sources, donor_map, by_id,
                        label_ids, execution, ledger,
                    )
                    all_results.append(result)
                    stream.write(json.dumps(result, sort_keys=True, allow_nan=False) + "\n")
                    stream.flush()
    controls = _run_message_controls(adapter, rows, label_ids, ledger)
    if len(controls) != plan["message_control_execution_count"]:
        raise ValueError("QCI audit message-control count differs from frozen plan")
    expected_count = int(protocol["support_rule"]["expected_case_count"])
    assessments = [
        assess_candidate(
            [row for row in all_results if row["candidate_id"] == f"{candidate.agent}.{candidate.candidate_id}"],
            base["support_thresholds"], expected_count=expected_count,
        )
        for candidate in candidates
    ]
    supported = [row["candidate_id"] for row in assessments if row["status"] == "supported"]
    summary = {
        "schema_version": "aether.qci-audit.v1",
        "experiment_id": EXPERIMENT_ID,
        "run_id": RUN_ID,
        "utc_timestamp": datetime.now(timezone.utc).isoformat(),
        "model_id": base["model_id"],
        "model_revision": base["model_revision"],
        "protocol_hash": sha256_file(AUDIT_PROTOCOL_PATH),
        "discovery_summary_hash": sha256_file(discovery_root / "summary.json"),
        "development_audit_case_ids": [row["case_id"] for row in rows],
        "candidate_ids": plan["candidate_ids"],
        "excluded_supported_candidates": plan["excluded_supported_candidates"],
        "audit_supported_candidates": supported,
        "candidate_execution_count": len(all_results),
        "message_positive_control_count": len(controls),
        "development_audit_executions": len(all_results) + len(controls),
        "invalid_or_error_count": sum(row["status"] != "ok" for row in all_results),
        "validation_executions": 0,
        "test_executions": 0,
        "query_ledger": asdict(ledger),
        "runtime_seconds": time.perf_counter() - started,
        "next_state": protocol["next_state_if_supported"] if supported else protocol["next_state_if_rejected"],
        "claim_boundary": protocol["claim_boundary"],
    }
    controls_path = output_root / "message_positive_controls.json"
    assessments_path = output_root / "candidate_audit_assessments.json"
    summary_path = output_root / "summary.json"
    _write_json(controls_path, controls)
    _write_json(assessments_path, assessments)
    _write_json(summary_path, summary)
    marker["state"] = "QCI_AUDIT_COMPLETE"
    marker["utc_timestamp"] = summary["utc_timestamp"]
    _write_json(marker_path, marker)
    packages, environment_hash = _environment_inventory()
    manifest = {
        "manifest_version": "1.0.0",
        "experiment_id": EXPERIMENT_ID,
        "run_id": RUN_ID,
        "utc_timestamp": summary["utc_timestamp"],
        "git_commit": _git("rev-parse", "HEAD"),
        "uncommitted_diff": bool(_git("diff", "--name-only")),
        "dataset_manifest_hashes": preflight_record["dataset_manifest_hashes"],
        "model_id": base["model_id"],
        "model_revision": base["model_revision"],
        "tokenizer_revision": base["model_revision"],
        "prompt_versions": {"qualification": "V2.1"},
        "random_seeds": [42],
        "hardware": platform.platform(),
        "python_env_hash": environment_hash,
        "python_packages": packages,
        "command_line": sys.argv,
        "config_file": str(AUDIT_PROTOCOL_PATH.relative_to(ROOT)),
        "raw_output_path": str(raw_path),
        "artifact_paths": {
            str(path): sha256_file(path) for path in (
                raw_path, controls_path, assessments_path, summary_path,
                preflight_path, marker_path, snapshot_path,
            )
        },
    }
    _write_json(output_root / "manifest.json", manifest)
    return summary


def main() -> None:
    """Run QCI audit preflight or the authorized development-only campaign."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--discovery", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=OUTPUT_DEFAULT)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--preflight-only", action="store_true")
    arguments = parser.parse_args()
    try:
        function = preflight if arguments.preflight_only else run
        result = function(
            arguments.output.resolve(), arguments.cache.resolve(), arguments.discovery.resolve()
        )
        print(json.dumps(result, indent=2, sort_keys=True))
    except Exception as error:
        arguments.output.mkdir(parents=True, exist_ok=True)
        failure_path = arguments.output / "execution_failure.json"
        failure = {
            "schema_version": "aether.qci-audit-failure.v1",
            "experiment_id": EXPERIMENT_ID,
            "run_id": RUN_ID,
            "utc_timestamp": datetime.now(timezone.utc).isoformat(),
            "exception_type": type(error).__name__,
            "message": str(error),
            "traceback": traceback.format_exc(),
            "git_commit": _git("rev-parse", "HEAD"),
            "uncommitted_diff": bool(_git("diff", "--name-only")),
            "model_id": json.loads(BASE_PROTOCOL_PATH.read_text(encoding="utf-8"))["model_id"],
            "model_revision": json.loads(BASE_PROTOCOL_PATH.read_text(encoding="utf-8"))["model_revision"],
            "tokenizer_revision": json.loads(BASE_PROTOCOL_PATH.read_text(encoding="utf-8"))["model_revision"],
            "random_seeds": [42],
            "config_file": str(AUDIT_PROTOCOL_PATH.relative_to(ROOT)),
            "config_hash": sha256_file(AUDIT_PROTOCOL_PATH),
            "development_audit_executions": _completed_audit_executions(arguments.output),
            "validation_executions": 0,
            "test_executions": 0,
        }
        _write_json(failure_path, failure)
        packages, environment_hash = _environment_inventory()
        _write_json(arguments.output / "failure_manifest.json", {
            "manifest_version": "1.0.0",
            "experiment_id": EXPERIMENT_ID,
            "run_id": RUN_ID,
            "utc_timestamp": failure["utc_timestamp"],
            "git_commit": failure["git_commit"],
            "uncommitted_diff": failure["uncommitted_diff"],
            "dataset_manifest_hashes": {},
            "model_id": failure["model_id"],
            "model_revision": failure["model_revision"],
            "tokenizer_revision": failure["tokenizer_revision"],
            "prompt_versions": {"qualification": "V2.1"},
            "random_seeds": [42],
            "hardware": platform.platform(),
            "python_env_hash": environment_hash,
            "python_packages": packages,
            "command_line": sys.argv,
            "config_file": failure["config_file"],
            "raw_output_path": str(failure_path),
            "artifact_paths": {str(failure_path): sha256_file(failure_path)},
        })
        raise


if __name__ == "__main__":
    main()
