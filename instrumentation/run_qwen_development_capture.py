"""Capture prospectively declared Qwen sender/receiver development activations."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import platform
import subprocess
import sys
import time
import traceback
from typing import Any

import psutil
import torch
import torch.nn.functional as functional

from experiments.manifest import sha256_file
from instrumentation.adapters import Qwen2ModelAdapter
from paired_trace.metrics import validate_label_tokens
from paired_trace.run_model_qualification import (
    _cgroup_memory,
    _environment_inventory,
    _validate_model_candidate,
    _verify_snapshot_manifest,
    measure_hardware,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs/model_qualification/qwen_1_5b_development_capture.json"
OUTPUT_DEFAULT = ROOT / "results/phase1/development_capture/qwen15b_dcap1"
EXPERIMENT_ID = "P0_mech_20261111_qwen15b_dcap1"
RUN_ID = "P0_mech_20261111_qwen15b_dcap1_seed42"


def _write_json(path: Path, value: Any) -> None:
    """Write strict JSON with stable formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _git(*arguments: str) -> str:
    """Return required Git metadata from this checkout."""
    return subprocess.run(
        ["git", *arguments], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def _load_inputs() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Verify IA-G1 and return the exact prospective development rows."""
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if config.get("status") != "prospectively_frozen_before_broad_activation_capture":
        raise ValueError("development capture config is not prospectively frozen")
    candidate = _validate_model_candidate(config["model_id"])
    if candidate["revision"] != config["model_revision"]:
        raise ValueError("capture model differs from the qualified revision")
    acceptance = ROOT / config["acceptance_directory"]
    summary_path, manifest_path = acceptance / "summary.json", acceptance / "manifest.json"
    if sha256_file(summary_path) != config["instrumentation_acceptance_summary_sha256"]:
        raise ValueError("IA-G1 summary hash differs from prospective capture input")
    if sha256_file(manifest_path) != config["instrumentation_acceptance_manifest_sha256"]:
        raise ValueError("IA-G1 manifest hash differs from prospective capture input")
    acceptance_summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if (
        acceptance_summary.get("overall") != "PASS"
        or acceptance_summary.get("run_id") != config["instrumentation_acceptance_run_id"]
        or acceptance_summary.get("validation_executions") != 0
        or acceptance_summary.get("test_executions") != 0
    ):
        raise ValueError("IA-G1 prerequisite did not pass with locked splits")
    partitions = (
        config["excluded_acceptance_case_ids"],
        config["discovery_case_ids"],
        config["development_audit_case_ids"],
    )
    flattened = [case_id for partition in partitions for case_id in partition]
    if len(flattened) != 24 or len(set(flattened)) != 24:
        raise ValueError("capture partitions must disjointly cover all 24 qualified cases")
    qualification = ROOT / config["qualification_directory"]
    rows = json.loads((qualification / "mq_g1_rows.json").read_text(encoding="utf-8"))
    by_id = {row["case_id"]: row for row in rows}
    capture_ids = config["discovery_case_ids"] + config["development_audit_case_ids"]
    selected = [by_id[case_id] for case_id in capture_ids]
    if any(row["split"] != "development" or not row["eligible"] for row in selected):
        raise ValueError("capture cohort contains an ineligible or non-development row")
    for name in ("discovery_case_ids", "development_audit_case_ids"):
        directions = [by_id[case_id]["direction"] for case_id in config[name]]
        if directions.count("A_TO_B") != directions.count("B_TO_A"):
            raise ValueError(f"{name} is not directionally balanced")
    return config, selected


def preflight(output_root: Path, cache_root: Path) -> dict[str, Any]:
    """Verify prerequisites and resources before any model repository access."""
    config, rows = _load_inputs()
    hardware = measure_hardware(cache_root)
    packages, environment_hash = _environment_inventory()
    result = {
        "schema_version": "aether.development-capture-preflight.v1",
        "experiment_id": EXPERIMENT_ID, "run_id": RUN_ID,
        "utc_timestamp": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git("rev-parse", "HEAD"),
        "uncommitted_diff": bool(_git("status", "--porcelain")),
        "model_id": config["model_id"], "model_revision": config["model_revision"],
        "tokenizer_revision": config["model_revision"],
        "random_seeds": [config["execution"]["seed"]],
        "python_version": platform.python_version(), "python_executable": sys.executable,
        "python_env_hash": environment_hash, "python_packages": packages,
        "command_line": sys.argv, "config_file": str(CONFIG_PATH.relative_to(ROOT)),
        "config_hash": sha256_file(CONFIG_PATH),
        "dataset_manifest_hashes": {
            "ia_summary": config["instrumentation_acceptance_summary_sha256"],
            "ia_manifest": config["instrumentation_acceptance_manifest_sha256"],
        },
        "subset_ids": [row["case_id"] for row in rows],
        "model_accessed": False, "hardware": hardware,
        "decision": {
            "inputs_verified": True,
            "hardware_pass": hardware["decision"]["overall"] == "PASS",
            "overall": "PASS" if hardware["decision"]["overall"] == "PASS" else "BLOCKED",
        },
        "raw_output_path": str(output_root / "capture_preflight.json"),
    }
    output_root.mkdir(parents=True, exist_ok=True)
    _write_json(output_root / "capture_preflight.json", result)
    return result


def _prompt(row: dict[str, Any], agent: str, condition: str) -> tuple[str, list[int]]:
    """Return the exact qualified prompt and token IDs for one trace leg."""
    if agent == "sender":
        prompt_key = f"{condition}_sender_prompt"
        ids_key = "sender_prompt_token_ids" if condition == "clean" else "attacked_sender_prompt_token_ids"
    elif agent == "receiver":
        prompt_key = f"{condition}_receiver_prompt"
        ids_key = f"{condition}_receiver_prompt_token_ids"
    else:
        raise ValueError(f"unknown agent region: {agent}")
    return str(row[prompt_key]), [int(token) for token in row[ids_key]]


def _capture_one(
    adapter: Qwen2ModelAdapter,
    prompt: str,
    expected_ids: list[int],
    config: dict[str, Any],
    path: Path,
    label_ids: dict[str, int],
    expected_code: str,
    agent: str,
) -> tuple[dict[str, torch.Tensor], dict[str, Any]]:
    """Capture one prompt at every declared module and head site."""
    inputs = adapter.tokenize([prompt])
    actual_ids = [int(token) for token in inputs["input_ids"][0].tolist()]
    if actual_ids != expected_ids:
        raise ValueError("capture tokenization differs from qualified prompt token IDs")
    sites = [
        site for site in adapter.identify_components(config["layers"])
        if site.component_type in config["module_components"]
    ]
    try:
        adapter.install_comprehensive_capture(sites, config["layers"])
        final_logits = adapter.forward(inputs).logits[:, -1, :].detach().cpu().clone()
        modules = dict(adapter.activations)
        heads = dict(adapter.head_activations)
    finally:
        adapter.remove_hooks()
    position = config["token_position"]
    payload = {
        **{f"module.{key}": value[:, position, :].contiguous() for key, value in modules.items()},
        **{f"head.{key}": value[:, position, :, :].contiguous() for key, value in heads.items()},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(payload, path)
    restored = torch.load(path, map_location="cpu", weights_only=True)
    if set(restored) != set(payload) or any(not torch.equal(payload[key], restored[key]) for key in payload):
        raise ValueError("captured activation artifact failed exact tensor round trip")
    if agent == "receiver":
        predicted = "A" if float(final_logits[0, label_ids["A"]]) >= float(final_logits[0, label_ids["B"]]) else "B"
    else:
        predicted = adapter.tokenizer.decode(
            [int(final_logits.argmax(dim=-1)[0])], skip_special_tokens=True
        ).strip()
    return payload, {
        "path": str(path), "sha256": sha256_file(path),
        "component_count": len(payload),
        "module_component_count": len(modules), "head_layer_count": len(heads),
        "input_token_count": len(actual_ids), "input_token_ids": actual_ids,
        "predicted_code": predicted, "expected_qualified_code": expected_code,
        "prediction_matches_qualification": predicted == expected_code,
        "round_trip_exact": True, "hooks_remaining": len(adapter._handles),
    }


def _paired_measurements(
    clean: dict[str, torch.Tensor], attacked: dict[str, torch.Tensor]
) -> list[dict[str, Any]]:
    """Compute declared descriptive clean/attack distances without ranking."""
    if set(clean) != set(attacked):
        raise ValueError("paired activation component sets differ")
    rows: list[dict[str, Any]] = []
    for component_id in sorted(clean):
        left, right = clean[component_id].float().reshape(-1), attacked[component_id].float().reshape(-1)
        cosine = float(functional.cosine_similarity(left[None], right[None])[0])
        distance = float(torch.linalg.vector_norm(left - right))
        if not math.isfinite(cosine) or not math.isfinite(distance):
            raise ValueError(f"non-finite activation measurement: {component_id}")
        rows.append({
            "component_id": component_id,
            "l2_distance": distance,
            "cosine_similarity": cosine,
        })
    return rows


def run(output_root: Path, cache_root: Path) -> dict[str, Any]:
    """Capture all frozen development traces using one pinned model load."""
    started = time.perf_counter()
    config, rows = _load_inputs()
    preflight_path = output_root / "capture_preflight.json"
    marker_path = output_root / "capture_model_access.json"
    if not preflight_path.is_file() or not marker_path.is_file():
        raise RuntimeError("run capture preflight and snapshot access first")
    preflight_record = json.loads(preflight_path.read_text(encoding="utf-8"))
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    if preflight_record["decision"]["overall"] != "PASS":
        raise RuntimeError("capture preflight did not pass")
    if marker.get("preflight_sha256") != sha256_file(preflight_path):
        raise RuntimeError("capture preflight differs from model-access marker")
    if marker.get("state") != "MODEL_FILES_READY":
        raise RuntimeError("capture model-access marker is not ready")
    snapshot_path = Path(marker["snapshot_manifest_path"])
    if sha256_file(snapshot_path) != marker["snapshot_manifest_sha256"]:
        raise RuntimeError("capture snapshot manifest differs from marker")
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    if snapshot.get("model_id") != config["model_id"] or snapshot.get("resolved_revision") != config["model_revision"]:
        raise RuntimeError("capture snapshot is not the frozen model revision")
    _verify_snapshot_manifest(snapshot, cache_root)
    if torch.version.cuda is not None or torch.cuda.is_available():
        raise RuntimeError("DCAP-1 requires the qualified CPU-only condition")
    torch.manual_seed(config["execution"]["seed"])
    torch.set_num_threads(2)
    adapter = Qwen2ModelAdapter(
        config["model_id"], config["model_revision"], cache_root,
        dtype=torch.float32, device="cpu", local_files_only=True,
        low_cpu_mem_usage=True,
    )
    adapter.load()
    available = psutil.virtual_memory().available / 2**30
    _limit, cgroup_available = _cgroup_memory()
    effective = min(value for value in (available, cgroup_available) if value is not None)
    if effective < config["minimum_post_load_available_memory_gib"]:
        raise MemoryError("post-load memory is below the DCAP-1 minimum")
    if len(adapter.model.model.layers) != len(config["layers"]):
        raise ValueError("loaded architecture differs from frozen 28-layer capture scope")
    label_ids = validate_label_tokens(adapter.tokenizer)
    artifacts: list[dict[str, Any]] = []
    measurements: list[dict[str, Any]] = []
    for row in rows:
        partition = "discovery" if row["case_id"] in config["discovery_case_ids"] else "development_audit"
        for agent in config["agents"]:
            captured: dict[str, dict[str, torch.Tensor]] = {}
            for condition in config["conditions"]:
                prompt, token_ids = _prompt(row, agent, condition)
                expected_code = row[f"{condition}_{agent}_output"] if agent == "sender" else row[f"{condition}_{agent}_code"]
                path = output_root / "activations" / f"{row['case_id']}_{agent}_{condition}.pt"
                payload, record = _capture_one(
                    adapter, prompt, token_ids, config, path, label_ids,
                    str(expected_code), agent,
                )
                captured[condition] = payload
                artifacts.append({
                    **record, "case_id": row["case_id"], "direction": row["direction"],
                    "partition": partition, "agent": agent, "condition": condition,
                    "token_position": config["token_position"],
                })
            for measurement in _paired_measurements(captured["clean"], captured["attacked"]):
                measurements.append({
                    "case_id": row["case_id"], "direction": row["direction"],
                    "partition": partition, "agent": agent, **measurement,
                })
    predicates = {
        "DCAP-1.1_ia_g1_verified": True,
        "DCAP-1.2_all_declared_traces_captured": len(artifacts) == len(rows) * 4,
        "DCAP-1.3_artifact_round_trip": all(item["round_trip_exact"] for item in artifacts),
        "DCAP-1.4_qualified_predictions_reproduced": all(item["prediction_matches_qualification"] for item in artifacts),
        "DCAP-1.5_hook_cleanup": all(item["hooks_remaining"] == 0 for item in artifacts),
        "DCAP-1.6_locked_splits_unopened": True,
        "DCAP-1.7_audit_partition_not_ranked": True,
    }
    overall = "PASS" if all(predicates.values()) else "FAIL"
    measurements_path = output_root / "paired_activation_measurements.json"
    artifacts_path = output_root / "activation_artifacts.json"
    _write_json(measurements_path, measurements)
    _write_json(artifacts_path, artifacts)
    summary = {
        "schema_version": "aether.development-capture.v1",
        "experiment_id": EXPERIMENT_ID, "run_id": RUN_ID,
        "utc_timestamp": datetime.now(timezone.utc).isoformat(),
        "model_id": config["model_id"], "model_revision": config["model_revision"],
        "dataset_split": "development", "discovery_case_ids": config["discovery_case_ids"],
        "development_audit_case_ids": config["development_audit_case_ids"],
        "excluded_acceptance_case_ids": config["excluded_acceptance_case_ids"],
        "validation_executions": 0, "test_executions": 0,
        "activation_artifact_count": len(artifacts),
        "paired_measurement_count": len(measurements),
        "predicates": predicates, "overall": overall,
        "runtime_seconds": time.perf_counter() - started,
        "claim_boundary": config["claim_boundary"],
        "next_state": "READY_FOR_PROSPECTIVE_CAUSAL_INTERVENTION_PROTOCOL_REVIEW"
        if overall == "PASS" else "CAPTURE_INCOMPLETE_STOP",
    }
    summary_path = output_root / "summary.json"
    _write_json(summary_path, summary)
    marker["state"] = "DCAP_1_PASS" if overall == "PASS" else "DCAP_1_FAIL"
    marker["utc_timestamp"] = datetime.now(timezone.utc).isoformat()
    _write_json(marker_path, marker)
    packages, environment_hash = _environment_inventory()
    files = [summary_path, measurements_path, artifacts_path, preflight_path, marker_path, snapshot_path]
    files.extend(Path(item["path"]) for item in artifacts)
    manifest = {
        "manifest_version": "1.0.0", "experiment_id": EXPERIMENT_ID,
        "run_id": RUN_ID, "utc_timestamp": summary["utc_timestamp"],
        "git_commit": _git("rev-parse", "HEAD"),
        "uncommitted_diff": bool(_git("status", "--porcelain")),
        "dataset_manifest_hashes": {
            "ia_summary": config["instrumentation_acceptance_summary_sha256"],
            "ia_manifest": config["instrumentation_acceptance_manifest_sha256"],
        },
        "model_id": config["model_id"], "model_revision": config["model_revision"],
        "tokenizer_revision": config["model_revision"], "random_seeds": [config["execution"]["seed"]],
        "hardware": platform.platform(), "python_version": platform.python_version(),
        "python_executable": sys.executable, "python_env_hash": environment_hash,
        "python_packages": packages, "command_line": sys.argv,
        "config_file": str(CONFIG_PATH.relative_to(ROOT)), "config_hash": sha256_file(CONFIG_PATH),
        "raw_output_path": str(summary_path),
        "artifact_paths": {str(path): sha256_file(path) for path in files},
        "timing_seconds": {"total": summary["runtime_seconds"]},
    }
    _write_json(output_root / "manifest.json", manifest)
    return summary


def _write_failure_manifest(output_root: Path, error: Exception) -> None:
    """Retain required provenance for a failed DCAP-1 attempt."""
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    packages, environment_hash = _environment_inventory()
    artifacts = [path for path in output_root.rglob("*") if path.is_file() and path.name != "failure_manifest.json"]
    _write_json(output_root / "failure_manifest.json", {
        "manifest_version": "1.0.0", "experiment_id": EXPERIMENT_ID,
        "run_id": RUN_ID, "utc_timestamp": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git("rev-parse", "HEAD"), "uncommitted_diff": bool(_git("status", "--porcelain")),
        "dataset_manifest_hashes": {"ia_summary": config["instrumentation_acceptance_summary_sha256"]},
        "model_id": config["model_id"], "model_revision": config["model_revision"],
        "tokenizer_revision": config["model_revision"], "random_seeds": [config["execution"]["seed"]],
        "hardware": platform.platform(), "python_version": platform.python_version(),
        "python_executable": sys.executable, "python_env_hash": environment_hash,
        "python_packages": packages, "command_line": sys.argv,
        "config_file": str(CONFIG_PATH.relative_to(ROOT)), "config_hash": sha256_file(CONFIG_PATH),
        "raw_output_path": str(output_root / "execution_failure.json"),
        "artifact_paths": {str(path): sha256_file(path) for path in artifacts},
        "failure": {"exception_type": type(error).__name__, "message": str(error)},
    })


def main() -> None:
    """Run DCAP-1 preflight or its one-load capture campaign."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT_DEFAULT)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--preflight-only", action="store_true")
    arguments = parser.parse_args()
    output, cache = arguments.output.resolve(), arguments.cache.resolve()
    try:
        result = preflight(output, cache) if arguments.preflight_only else run(output, cache)
    except Exception as error:
        output.mkdir(parents=True, exist_ok=True)
        _write_json(output / "execution_failure.json", {
            "utc_timestamp": datetime.now(timezone.utc).isoformat(),
            "exception_type": type(error).__name__, "message": str(error),
            "traceback": traceback.format_exc(),
        })
        _write_failure_manifest(output, error)
        raise
    print(json.dumps(result, indent=2, allow_nan=False))
    state = result.get("overall") or result.get("decision", {}).get("overall")
    if state in {"FAIL", "BLOCKED"}:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
