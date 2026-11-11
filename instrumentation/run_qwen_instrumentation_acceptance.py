"""Run the prospective Qwen 1.5B instrumentation-acceptance gate.

This development-only gate verifies hook compatibility and intervention
mechanics after behavioral qualification. It does not localize or rank a
circuit, run search, access locked splits, or authorize a scientific claim.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
import traceback
from typing import Any

import psutil
import torch

from experiments.manifest import sha256_file
from instrumentation.adapters import Qwen2ModelAdapter
from paired_trace.metrics import escalation_margin, validate_label_tokens
from paired_trace.run_model_qualification import (
    _cgroup_memory,
    _environment_inventory,
    _validate_model_candidate,
    _verify_snapshot_manifest,
    measure_hardware,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs/model_qualification/qwen_1_5b_instrumentation_acceptance.json"
MODEL_CONFIG_PATH = ROOT / "configs/model_qualification/qwen_1_5b_candidate.json"
OUTPUT_DEFAULT = ROOT / "results/phase1/instrumentation_acceptance/qwen15b_ia_g1"
EXPERIMENT_ID = "P0_mech_20261111_qwen15b_ia_g1"
RUN_ID = "P0_mech_20261111_qwen15b_ia_g1_seed42"


def _write_json(path: Path, value: Any) -> None:
    """Write strict, stable JSON and reject non-finite values."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _git(*arguments: str) -> str:
    """Return required Git metadata from the repository checkout."""
    return subprocess.run(
        ["git", *arguments], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def _load_config() -> dict[str, Any]:
    """Load and structurally validate the prospective acceptance config."""
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if config.get("status") != "prospectively_frozen_before_instrumentation_execution":
        raise ValueError("instrumentation acceptance config is not prospectively frozen")
    candidate = _validate_model_candidate(config["model_id"])
    if candidate["revision"] != config["model_revision"]:
        raise ValueError("instrumentation model revision differs from qualified candidate")
    execution = config["execution"]
    required_execution = {
        "device": "cpu", "dtype": "float32", "quantized": False,
        "offload": False, "attention_implementation": "eager", "seed": 42,
    }
    if execution != required_execution:
        raise ValueError("instrumentation execution settings differ from prospective policy")
    if config["dataset_split"] != "development":
        raise PermissionError("instrumentation acceptance is development-only")
    policy = config["split_access_policy"]
    if policy.get("validation") != "forbidden" or policy.get("test") != "forbidden":
        raise PermissionError("validation and test must remain forbidden")
    selected = config["selected_case_ids"]
    intervention = config["intervention_case_ids"]
    if len(selected) != len(set(selected)) or len(intervention) != len(set(intervention)):
        raise ValueError("acceptance case IDs must be unique")
    if not set(intervention).issubset(selected):
        raise ValueError("intervention cases must be drawn from the fixed acceptance cohort")
    return config


def verify_qualification_bundle(config: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Verify the ingested qualification decision and every hashed raw artifact."""
    directory = ROOT / config["qualification_directory"]
    summary_path = directory / "summary.json"
    manifest_path = directory / "manifest.json"
    if sha256_file(summary_path) != config["qualification_summary_sha256"]:
        raise ValueError("qualified summary hash differs from the frozen acceptance input")
    if sha256_file(manifest_path) != config["qualification_manifest_sha256"]:
        raise ValueError("qualified manifest hash differs from the frozen acceptance input")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    required = {
        "decision": summary.get("decision") == "QUALIFIED_FOR_SEPARATE_INSTRUMENTATION_REVIEW",
        "state": summary.get("model_access_state") == "MQ_G2_PASS",
        "g1": summary.get("mq_g1", {}).get("overall") == "PASS",
        "g2": summary.get("mq_g2", {}).get("overall") == "PASS",
        "model": summary.get("model_id") == config["model_id"],
        "revision": summary.get("model_revision") == config["model_revision"],
        "run_id": summary.get("run_id") == config["qualification_run_id"],
        "git_commit": manifest.get("git_commit") == config["qualification_git_commit"],
        "clean_source": manifest.get("uncommitted_diff") is False,
        "development": summary.get("dataset", {}).get("split") == "development",
        "validation_closed": summary.get("validation_executions") == 0,
        "test_closed": summary.get("test_executions") == 0,
        "no_prior_internal_interventions": summary.get("internal_interventions") is False,
    }
    failed = [name for name, passed in required.items() if not passed]
    if failed:
        raise ValueError(f"qualification bundle violates acceptance prerequisites: {failed}")
    for recorded, expected in manifest["artifact_paths"].items():
        local = directory / Path(recorded).name
        if not local.is_file() or sha256_file(local) != expected:
            raise ValueError(f"qualification artifact integrity mismatch: {local.name}")
    rows = json.loads((directory / "mq_g1_rows.json").read_text(encoding="utf-8"))
    by_id = {row["case_id"]: row for row in rows}
    if len(by_id) != len(rows):
        raise ValueError("qualification rows contain duplicate case IDs")
    missing = set(config["selected_case_ids"]) - set(by_id)
    if missing:
        raise ValueError(f"fixed acceptance cases are missing: {sorted(missing)}")
    selected = [by_id[case_id] for case_id in config["selected_case_ids"]]
    if any(row.get("split") != "development" or not row.get("eligible") for row in selected):
        raise ValueError("fixed instrumentation cohort is not eligible development data")
    directions = [row["direction"] for row in selected]
    if directions.count("A_TO_B") != directions.count("B_TO_A"):
        raise ValueError("fixed instrumentation cohort is directionally imbalanced")
    return summary, selected


def preflight(output_root: Path, cache_root: Path) -> dict[str, Any]:
    """Verify inputs and resources before any instrumentation-stage model access."""
    config = _load_config()
    qualification, selected = verify_qualification_bundle(config)
    hardware = measure_hardware(cache_root)
    result = {
        "schema_version": "aether.instrumentation-acceptance-preflight.v1",
        "utc_timestamp": datetime.now(timezone.utc).isoformat(),
        "experiment_id": EXPERIMENT_ID,
        "run_id": RUN_ID,
        "config_sha256": sha256_file(CONFIG_PATH),
        "qualification_summary_sha256": config["qualification_summary_sha256"],
        "qualification_run_id": qualification["run_id"],
        "selected_case_ids": [row["case_id"] for row in selected],
        "model_accessed": False,
        "hardware": hardware,
        "decision": {
            "qualification_verified": True,
            "hardware_pass": hardware["decision"]["overall"] == "PASS",
            "overall": "PASS" if hardware["decision"]["overall"] == "PASS" else "BLOCKED",
        },
    }
    output_root.mkdir(parents=True, exist_ok=True)
    _write_json(output_root / "instrumentation_preflight.json", result)
    return result


def _final_logits(adapter: Qwen2ModelAdapter, prompt: str) -> tuple[torch.Tensor, list[int]]:
    """Return detached final-position logits and exact input token IDs."""
    inputs = adapter.tokenize([prompt])
    logits = adapter.forward(inputs).logits[:, -1, :].detach().cpu().clone()
    return logits, [int(token) for token in inputs["input_ids"][0].tolist()]


def _activation_record(path: Path, tensor: torch.Tensor, semantics: str) -> dict[str, Any]:
    """Persist one selected activation tensor and verify its exact round trip."""
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(tensor.detach().cpu(), path)
    restored = torch.load(path, map_location="cpu", weights_only=True)
    return {
        "path": str(path), "sha256": sha256_file(path),
        "shape": list(tensor.shape), "dtype": str(tensor.dtype),
        "semantics": semantics, "round_trip_exact": torch.equal(tensor.cpu(), restored),
    }


def _passive_acceptance(
    adapter: Qwen2ModelAdapter,
    rows: list[dict[str, Any]],
    config: dict[str, Any],
    output_root: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Check passive equivalence and persist fixed last-token captures."""
    sites = [
        site for site in adapter.identify_components(config["capture_layers"])
        if site.component_type in config["capture_component_types"]
    ]
    results: list[dict[str, Any]] = []
    artifacts: list[dict[str, Any]] = []
    for row in rows:
        for condition in ("clean", "attacked"):
            prompt = row[f"{condition}_receiver_prompt"]
            baseline, token_ids = _final_logits(adapter, prompt)
            inputs = adapter.tokenize([prompt])
            try:
                adapter.install_capture_hooks(sites)
                observed = adapter.forward(inputs).logits[:, -1, :].detach().cpu().clone()
                captures = dict(adapter.activations)
            finally:
                adapter.remove_hooks()
            max_difference = float((baseline - observed).abs().max())
            allclose = torch.allclose(
                baseline, observed,
                rtol=config["passive_logit_rtol"], atol=config["passive_logit_atol"],
            )
            argmax_equal = torch.equal(baseline.argmax(dim=-1), observed.argmax(dim=-1))
            for site in sites:
                selected = captures[site.component_id][:, -1, :]
                artifacts.append(_activation_record(
                    output_root / "activations" / f"{row['case_id']}_{condition}_{site.component_id}.pt",
                    selected,
                    f"{site.tensor_semantics}; final prompt token only",
                ))
            results.append({
                "case_id": row["case_id"], "direction": row["direction"],
                "condition": condition, "input_token_ids": token_ids,
                "site_count": len(sites), "max_logit_difference": max_difference,
                "argmax_equal": argmax_equal, "allclose": allclose,
                "hooks_remaining": len(adapter._handles),
            })
    return results, artifacts


def _head_acceptance(
    adapter: Qwen2ModelAdapter,
    row: dict[str, Any],
    config: dict[str, Any],
    output_root: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Verify exact passive pre-o_proj head capture at the fixed layer."""
    prompt = row["clean_receiver_prompt"]
    baseline, _ = _final_logits(adapter, prompt)
    inputs = adapter.tokenize([prompt])
    layer = config["head_capture_layer"]
    try:
        adapter.install_head_capture(layer)
        observed = adapter.forward(inputs).logits[:, -1, :].detach().cpu().clone()
        concatenated = adapter.head_activations[f"L{layer}.pre_o_proj_concat"]
        heads = adapter.head_activations[f"L{layer}.pre_o_proj_heads"]
    finally:
        adapter.remove_hooks()
    artifact = _activation_record(
        output_root / "activations" / f"{row['case_id']}_clean_L{layer}_pre_o_proj_heads.pt",
        heads[:, -1, :, :],
        "per-head tensor immediately before Qwen attention o_proj; final prompt token only",
    )
    return {
        "case_id": row["case_id"], "layer": layer,
        "concat_shape": list(concatenated.shape), "heads_shape": list(heads.shape),
        "reconstructs_concat_exactly": torch.equal(heads.reshape_as(concatenated), concatenated),
        "max_logit_difference": float((baseline - observed).abs().max()),
        "allclose": torch.allclose(
            baseline, observed,
            rtol=config["passive_logit_rtol"], atol=config["passive_logit_atol"],
        ),
        "hooks_remaining": len(adapter._handles),
    }, artifact


def _intervention_acceptance(
    adapter: Qwen2ModelAdapter,
    rows: list[dict[str, Any]],
    config: dict[str, Any],
    label_ids: dict[str, int],
) -> list[dict[str, Any]]:
    """Execute fixed clean-to-attacked last-token activation patches."""
    by_id = {row["case_id"]: row for row in rows}
    layer = config["intervention_layer"]
    site = next(
        site for site in adapter.identify_components([layer])
        if site.component_type == config["intervention_component_type"]
    )
    results: list[dict[str, Any]] = []
    for case_id in config["intervention_case_ids"]:
        row = by_id[case_id]
        clean_inputs = adapter.tokenize([row["clean_receiver_prompt"]])
        attacked_inputs = adapter.tokenize([row["attacked_receiver_prompt"]])
        if clean_inputs["input_ids"].shape != attacked_inputs["input_ids"].shape:
            raise ValueError(f"paired receiver token shapes differ for {case_id}")
        try:
            adapter.install_capture_hooks([site])
            adapter.forward(clean_inputs)
            source = adapter.activations[site.component_id].clone()
        finally:
            adapter.remove_hooks()
        attacked = adapter.forward(attacked_inputs).logits[:, -1, :].detach().cpu().clone()
        try:
            adapter.install_activation_patch(
                site, source, [config["intervention_token_position"]]
            )
            patched = adapter.forward(attacked_inputs).logits[:, -1, :].detach().cpu().clone()
            applications = adapter.intervention_applications
        finally:
            adapter.remove_hooks()
        difference = float((attacked - patched).abs().max())
        results.append({
            "case_id": case_id, "direction": row["direction"],
            "site": site.component_id,
            "token_position": config["intervention_token_position"],
            "attacked_margin": float(escalation_margin(attacked[:, None, :], label_ids)[0]),
            "patched_margin": float(escalation_margin(patched[:, None, :], label_ids)[0]),
            "max_logit_difference": difference,
            "effect_nonzero": difference > 0.0,
            "intervention_applications": applications,
            "hooks_remaining": len(adapter._handles),
        })
    return results


def run(output_root: Path, cache_root: Path) -> dict[str, Any]:
    """Run one model load and the complete prospective IA-G1 acceptance gate."""
    started = time.perf_counter()
    output_root = output_root.resolve()
    cache_root = cache_root.resolve()
    config = _load_config()
    qualification, rows = verify_qualification_bundle(config)
    preflight_path = output_root / "instrumentation_preflight.json"
    marker_path = output_root / "instrumentation_model_access.json"
    if not preflight_path.is_file() or not marker_path.is_file():
        raise RuntimeError("run IA preflight and pinned snapshot download before model access")
    preflight_record = json.loads(preflight_path.read_text(encoding="utf-8"))
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    if preflight_record["decision"]["overall"] != "PASS":
        raise RuntimeError("instrumentation preflight did not pass")
    if marker.get("state") != "MODEL_FILES_READY":
        raise RuntimeError("instrumentation snapshot marker is not ready")
    if marker.get("model_revision") != config["model_revision"]:
        raise RuntimeError("instrumentation marker revision differs from frozen config")
    snapshot_path = Path(marker["snapshot_manifest_path"])
    if sha256_file(snapshot_path) != marker["snapshot_manifest_sha256"]:
        raise RuntimeError("snapshot manifest differs from the access marker")
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    _verify_snapshot_manifest(snapshot, cache_root)
    if torch.version.cuda is not None or torch.cuda.is_initialized() or torch.cuda.is_available():
        raise RuntimeError("IA-G1 requires the qualified CPU-only PyTorch condition")
    torch.manual_seed(config["execution"]["seed"])
    candidate = _validate_model_candidate(config["model_id"])
    adapter = Qwen2ModelAdapter(
        candidate["model_id"], candidate["revision"], cache_root,
        dtype=torch.float32, device="cpu", local_files_only=True,
        low_cpu_mem_usage=True,
    )
    adapter.load()
    memory = psutil.virtual_memory()
    _limit, cgroup_available = _cgroup_memory()
    available_gib = memory.available / 2**30
    effective_available = min(
        value for value in (available_gib, cgroup_available) if value is not None
    )
    if effective_available < config["minimum_post_load_available_memory_gib"]:
        raise MemoryError("post-load memory is below the prospective IA-G1 minimum")
    layer_count = len(adapter.model.model.layers)
    if any(layer < 0 or layer >= layer_count for layer in config["capture_layers"]):
        raise ValueError(f"prospective capture layer is outside loaded architecture: {layer_count}")
    label_ids = validate_label_tokens(adapter.tokenizer)
    passive, activation_artifacts = _passive_acceptance(adapter, rows, config, output_root)
    head, head_artifact = _head_acceptance(adapter, rows[0], config, output_root)
    activation_artifacts.append(head_artifact)
    interventions = _intervention_acceptance(adapter, rows, config, label_ids)
    passive_pass = all(
        item["allclose"] and item["argmax_equal"] and item["hooks_remaining"] == 0
        for item in passive
    )
    activation_pass = all(item["round_trip_exact"] for item in activation_artifacts)
    head_pass = (
        head["allclose"] and head["reconstructs_concat_exactly"]
        and head["hooks_remaining"] == 0
    )
    intervention_pass = all(
        item["intervention_applications"] >= config["minimum_intervention_applications_per_case"]
        and (item["effect_nonzero"] or not config["require_nonzero_intervention_logit_effect"])
        and item["hooks_remaining"] == 0
        for item in interventions
    )
    predicates = {
        "IA-G1.1_qualification_verified": True,
        "IA-G1.2_model_and_architecture_compatible": True,
        "IA-G1.3_post_load_memory": effective_available >= config["minimum_post_load_available_memory_gib"],
        "IA-G1.4_passive_non_interference": passive_pass,
        "IA-G1.5_activation_round_trip": activation_pass,
        "IA-G1.6_pre_o_proj_head_semantics": head_pass,
        "IA-G1.7_fixed_interventions_execute": intervention_pass,
        "IA-G1.8_hook_cleanup": len(adapter._handles) == 0,
        "IA-G1.9_locked_splits_unopened": True,
    }
    decision = "PASS" if all(predicates.values()) else "FAIL"
    result = {
        "schema_version": "aether.instrumentation-acceptance.v1",
        "experiment_id": EXPERIMENT_ID, "run_id": RUN_ID,
        "utc_timestamp": datetime.now(timezone.utc).isoformat(),
        "model_id": config["model_id"], "model_revision": config["model_revision"],
        "qualification_run_id": qualification["run_id"],
        "dataset_id": config["dataset_id"], "dataset_split": "development",
        "selected_case_ids": config["selected_case_ids"],
        "validation_executions": 0, "test_executions": 0,
        "execution": config["execution"], "loaded_layer_count": layer_count,
        "post_load_available_ram_gib": available_gib,
        "post_load_cgroup_available_gib": cgroup_available,
        "predicates": predicates, "overall": decision,
        "passive_checks": passive, "head_check": head,
        "intervention_checks": interventions,
        "activation_artifacts": activation_artifacts,
        "runtime_seconds": time.perf_counter() - started,
        "claim_boundary": config["claim_boundary"],
        "next_state": "READY_FOR_PROSPECTIVE_DEVELOPMENT_CAPTURE_PROTOCOL_REVIEW"
        if decision == "PASS" else "INSTRUMENTATION_INCOMPATIBLE_STOP",
    }
    summary_path = output_root / "summary.json"
    _write_json(summary_path, result)
    marker["state"] = "IA_G1_PASS" if decision == "PASS" else "IA_G1_FAIL"
    marker["utc_timestamp"] = datetime.now(timezone.utc).isoformat()
    _write_json(marker_path, marker)
    packages, env_hash = _environment_inventory()
    artifact_paths = [summary_path, preflight_path, marker_path, snapshot_path]
    artifact_paths.extend(Path(item["path"]) for item in activation_artifacts)
    manifest = {
        "manifest_version": "1.0.0", "experiment_id": EXPERIMENT_ID,
        "run_id": RUN_ID, "utc_timestamp": result["utc_timestamp"],
        "git_commit": _git("rev-parse", "HEAD"),
        "uncommitted_diff": bool(_git("status", "--porcelain")),
        "dataset_manifest_hashes": {
            str(CONFIG_PATH.relative_to(ROOT)): sha256_file(CONFIG_PATH),
            str((ROOT / config["qualification_directory"] / "summary.json").relative_to(ROOT)):
                config["qualification_summary_sha256"],
            str((ROOT / config["qualification_directory"] / "manifest.json").relative_to(ROOT)):
                config["qualification_manifest_sha256"],
        },
        "model_id": config["model_id"], "model_revision": config["model_revision"],
        "tokenizer_revision": config["model_revision"],
        "random_seeds": [config["execution"]["seed"]],
        "hardware": {"platform": platform.platform(), "cpu_count": os.cpu_count(),
                     "device": "CPU float32", "torch_cuda_available": torch.cuda.is_available()},
        "python_version": platform.python_version(), "python_executable": sys.executable,
        "python_env_hash": env_hash, "python_packages": packages,
        "command_line": sys.argv, "config_file": str(CONFIG_PATH.relative_to(ROOT)),
        "config_hash": sha256_file(CONFIG_PATH), "raw_output_path": str(summary_path),
        "artifact_paths": {str(path): sha256_file(path) for path in artifact_paths},
        "intervention_configuration": {
            "layer": config["intervention_layer"],
            "component_type": config["intervention_component_type"],
            "token_position": config["intervention_token_position"],
            "case_ids": config["intervention_case_ids"],
        },
        "timing_seconds": {"total": result["runtime_seconds"]},
    }
    _write_json(output_root / "manifest.json", manifest)
    return result


def main() -> None:
    """Run preflight or the complete instrumentation acceptance campaign."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT_DEFAULT)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--preflight-only", action="store_true")
    arguments = parser.parse_args()
    output = arguments.output.resolve()
    cache = arguments.cache.resolve()
    try:
        result = preflight(output, cache) if arguments.preflight_only else run(output, cache)
    except Exception as error:
        output.mkdir(parents=True, exist_ok=True)
        _write_json(output / "execution_failure.json", {
            "utc_timestamp": datetime.now(timezone.utc).isoformat(),
            "exception_type": type(error).__name__, "message": str(error),
            "traceback": traceback.format_exc(),
        })
        raise
    print(json.dumps(result, indent=2, allow_nan=False))
    if result.get("overall") == "FAIL" or result.get("decision", {}).get("overall") == "BLOCKED":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
