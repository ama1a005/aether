"""Execute the frozen V2 Qwen 1.5B model-qualification campaign.

This runner performs MQ-G1 and, only after MQ-G1 passes, MQ-G2. It does not
install activation hooks, inspect validation/test rows, or execute internal
interventions. Resource and single-attempt guards run before model access.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import time
import traceback
from typing import Any

import psutil
import torch

from experiments.manifest import sha256_file
from instrumentation.adapters import Qwen2ModelAdapter
from paired_trace.balanced_v2 import case_normalized_margin, require_v2_development
from paired_trace.metrics import validate_label_tokens
from paired_trace.model_qualification import (
    BehavioralAttempt,
    MessageAttempt,
    evaluate_mq_g1,
    evaluate_mq_g2,
    evaluate_mq_hw1,
    post_load_memory_state,
)
from paired_trace.run_foundation import _input, _receiver_prompt, _sender_prompt
from paired_trace.schemas import MediatorMessage

ROOT = Path(__file__).resolve().parents[1]
G1_PATH = ROOT / "configs/model_qualification/v2_mq_g1.json"
G2_PATH = ROOT / "configs/model_qualification/v2_mq_g2.json"
HW_PATH = ROOT / "configs/model_qualification/v2_mq_hw1.json"
V21_PATH = ROOT / "configs/experiments/balanced_v2_redesign_v2_1.json"
REGISTRY_PATH = ROOT / "data/causal_v2/case_registry.json"
MAPPING_PATH = ROOT / "data/causal_v2/control_mappings.json"
MODEL_CONFIG_PATH = ROOT / "configs/model_qualification/qwen_1_5b_candidate.json"
PROTOCOL_PATH = ROOT / "docs/MODEL_QUALIFICATION_PROTOCOL.md"
OUTPUT_DEFAULT = ROOT / "results/phase1/model_qualification/v2_mq_hw1_kaggle"
RUN_ID = "P0_target_20261110_qwen15b_mq_seed42"
EXPERIMENT_ID = "P0_target_20261110_qwen15b_mq"


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _repo_or_absolute(path: Path) -> str:
    """Render committed paths relatively and external protocol files absolutely."""
    resolved = path.resolve()
    return str(resolved.relative_to(ROOT)) if resolved.is_relative_to(ROOT) else str(resolved)


def _text_hashes_with_newline_variants(path: Path) -> dict[str, str]:
    """Return raw, canonical-LF, and canonical-CRLF hashes for a UTF-8 text file."""
    raw = path.read_bytes()
    crlf, lf, cr = bytes((13, 10)), bytes((10,)), bytes((13,))
    canonical_lf = raw.replace(crlf, lf).replace(cr, lf)
    canonical_crlf = canonical_lf.replace(lf, crlf)
    return {
        "raw_sha256": _sha256_bytes(raw),
        "canonical_lf_sha256": _sha256_bytes(canonical_lf),
        "canonical_crlf_sha256": _sha256_bytes(canonical_crlf),
    }


def _verify_frozen_text_hash(path: Path, expected: str, label: str) -> dict[str, str]:
    """Verify frozen content while allowing only LF/CRLF checkout conversion."""
    observed = _text_hashes_with_newline_variants(path)
    if expected not in observed.values():
        raise ValueError(
            f"frozen input hash mismatch for {label}: expected {expected}; observed {observed}"
        )
    return {"expected_frozen_sha256": expected, **observed}


def _canonical_text_sha256(path: Path) -> str:
    """Hash UTF-8 text using LF line endings for cross-platform manifests."""
    return _text_hashes_with_newline_variants(path)["canonical_lf_sha256"]


def _cgroup_memory() -> tuple[float | None, float | None]:
    """Return cgroup memory limit and available GiB when Linux exposes them."""
    root = Path("/sys/fs/cgroup")
    limit_path, current_path = root / "memory.max", root / "memory.current"
    if limit_path.is_file() and current_path.is_file():
        limit_text = limit_path.read_text(encoding="ascii").strip()
        if limit_text == "max":
            return None, None
        limit = int(limit_text)
        current = int(current_path.read_text(encoding="ascii").strip())
    else:
        limit_path = root / "memory" / "memory.limit_in_bytes"
        current_path = root / "memory" / "memory.usage_in_bytes"
        if not (limit_path.is_file() and current_path.is_file()):
            return None, None
        limit = int(limit_path.read_text(encoding="ascii").strip())
        if limit >= 2**60:
            return None, None
        current = int(current_path.read_text(encoding="ascii").strip())
    return limit / 2**30, max(0, limit - current) / 2**30


def measure_hardware(cache_path: Path) -> dict[str, Any]:
    """Measure the frozen pre-access resource gate and container headroom."""
    memory = psutil.virtual_memory()
    disk = shutil.disk_usage(cache_path)
    limit_gib, cgroup_available_gib = _cgroup_memory()
    values = {
        "installed_ram_gib": memory.total / 2**30,
        "available_ram_gib": memory.available / 2**30,
        "disk_free_gib": disk.free / 2**30,
    }
    gate = json.loads(HW_PATH.read_text(encoding="utf-8"))
    model_config = _validate_model_candidate(gate["candidate_model_id"])
    decision = evaluate_mq_hw1(values, gate)
    cgroup_ok = cgroup_available_gib is None or cgroup_available_gib >= gate[
        "minimum_pre_access_available_physical_ram_gib"
    ]
    return {
        "schema_version": "aether.mq-hw1-preflight.v2",
        "utc_timestamp": datetime.now(timezone.utc).isoformat(),
        "python_executable": sys.executable,
        "cache_path": str(cache_path.resolve()),
        "model_candidate_config": _repo_or_absolute(MODEL_CONFIG_PATH),
        "model_candidate_config_sha256": _canonical_text_sha256(MODEL_CONFIG_PATH),
        "model_revision": model_config["revision"],
        "model_accessed": False,
        "measurements": {
            **values,
            "cgroup_memory_limit_gib": limit_gib,
            "cgroup_available_gib": cgroup_available_gib,
        },
        "decision": {
            **decision,
            "predicates": {**decision["predicates"], "MQ-HW1.cgroup_headroom": cgroup_ok},
            "overall": "PASS" if decision["overall"] == "PASS" and cgroup_ok else "BLOCKED",
            "state": "READY_FOR_MODEL_ACCESS"
            if decision["overall"] == "PASS" and cgroup_ok
            else gate["pre_access_failure_state"],
        },
    }


def _validate_model_candidate(expected_model_id: str) -> dict[str, Any]:
    """Fail closed unless the sole revision matches frozen CPU-fp32 settings."""
    config = json.loads(MODEL_CONFIG_PATH.read_text(encoding="utf-8"))
    checks = {
        "status": config.get("status") == "frozen_for_authorized_campaign",
        "model_id": config.get("model_id") == expected_model_id,
        "revision": bool(re.fullmatch(r"[0-9a-f]{40}", str(config.get("revision", "")))),
        "device": config.get("device") == "cpu",
        "dtype": config.get("dtype") == "float32",
        "quantized": config.get("quantized") is False,
        "explicit_offload": config.get("explicit_offload") is False,
        "disk_offload": config.get("disk_offload") is False,
        "low_cpu_mem_usage": config.get("low_cpu_mem_usage") is True,
        "trust_remote_code": config.get("trust_remote_code") is False,
        "local_files_only": config.get("local_files_only") is True,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError(f"candidate config violates frozen MQ-HW1 execution: {failed}")
    return config


def _environment_inventory() -> tuple[list[str], str]:
    """Hash the actual installed distribution inventory without invoking pip."""
    packages = sorted(
        f"{distribution.metadata['Name']}=={distribution.version}"
        for distribution in importlib.metadata.distributions()
        if distribution.metadata.get("Name")
    )
    serialized = "\n".join(packages) + "\n"
    return packages, _sha256_bytes(serialized.encode("utf-8"))


def _verify_snapshot_manifest(manifest: dict[str, Any], cache_root: Path) -> None:
    """Re-hash the downloaded snapshot before model construction or tokenizer load."""
    snapshot = Path(manifest["snapshot_path"]).resolve()
    cache = cache_root.resolve()
    if not snapshot.is_relative_to(cache):
        raise ValueError("model snapshot path is outside the configured Hugging Face cache")
    if snapshot.name != manifest["resolved_revision"]:
        raise ValueError("snapshot directory does not match the declared immutable revision")
    records = manifest.get("files")
    if not isinstance(records, list) or not records:
        raise ValueError("snapshot manifest has no file records")
    expected = {record["path"]: record for record in records}
    if len(expected) != len(records):
        raise ValueError("snapshot manifest contains duplicate paths")
    actual_paths = {path.relative_to(snapshot).as_posix(): path
                    for path in snapshot.rglob("*") if path.is_file()}
    if set(actual_paths) != set(expected):
        raise ValueError("model snapshot file set differs from its hash manifest")
    for relative, path in actual_paths.items():
        resolved = path.resolve()
        if not resolved.is_relative_to(cache):
            raise ValueError(f"snapshot file resolves outside configured cache: {relative}")
        record = expected[relative]
        if path.stat().st_size != record["size"] or sha256_file(path) != record["sha256"]:
            raise ValueError(f"model snapshot integrity mismatch: {relative}")
    required = {"config.json", "model.safetensors", "tokenizer.json", "tokenizer_config.json"}
    if not required.issubset(expected):
        raise ValueError(f"model snapshot lacks required files: {sorted(required - set(expected))}")


def _git(command: list[str]) -> str:
    """Run a required git metadata command and return stdout."""
    return subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()


def _generation_codes(
    adapter: Qwen2ModelAdapter, generated: torch.Tensor, prompt_length: int
) -> tuple[list[str], list[list[int]], list[str]]:
    codes = [
        adapter.tokenizer.decode([int(row[prompt_length])], skip_special_tokens=True).strip()
        for row in generated
    ]
    token_ids = [[int(token) for token in row[prompt_length:].tolist()] for row in generated]
    full_outputs = [
        adapter.tokenizer.decode(row[prompt_length:], skip_special_tokens=True)
        for row in generated
    ]
    return codes, token_ids, full_outputs


def _score_valid_messages(
    adapter: Qwen2ModelAdapter,
    messages: list[MediatorMessage],
    label_ids: dict[str, int],
    correct_codes: list[str],
) -> dict[str, Any]:
    """Score only schema-valid messages; invalid outputs remain unscored failures."""
    valid_indices = [index for index, message in enumerate(messages) if message.valid]
    scores: list[float | None] = [None] * len(messages)
    predicted: list[str | None] = [None] * len(messages)
    raw_a_values: list[float | None] = [None] * len(messages)
    raw_b_values: list[float | None] = [None] * len(messages)
    prompts: list[str | None] = [None] * len(messages)
    input_ids: list[list[int] | None] = [None] * len(messages)
    if valid_indices:
        selected_prompts = [
            _receiver_prompt(adapter, messages[index].serialize()) for index in valid_indices
        ]
        inputs = adapter.tokenize(
            selected_prompts
        )
        logits = adapter.forward(inputs).logits
        margins, selected_raw_a, selected_raw_b = case_normalized_margin(
            logits, label_ids, [correct_codes[index] for index in valid_indices]
        )
        for local, original in enumerate(valid_indices):
            scores[original] = float(margins[local])
            predicted[original] = "A" if float(selected_raw_a[local]) >= float(selected_raw_b[local]) else "B"
            raw_a_values[original] = float(selected_raw_a[local])
            raw_b_values[original] = float(selected_raw_b[local])
            prompts[original] = selected_prompts[local]
            input_ids[original] = [int(token) for token in inputs["input_ids"][local].tolist()]
    return {
        "scores": scores, "predicted": predicted,
        "raw_a": raw_a_values, "raw_b": raw_b_values,
        "prompts": prompts, "input_ids": input_ids, "valid_indices": valid_indices,
    }


def _write_json(path: Path, value: Any) -> None:
    """Write strict JSON, rejecting NaN/Infinity instead of emitting invalid numbers."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False), encoding="utf-8")


def _log_event(output_root: Path, component: str, event: str, payload: dict[str, Any]) -> None:
    """Append one structured, timestamped experiment event."""
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "run_id": RUN_ID,
        "experiment_id": EXPERIMENT_ID,
        "component": component,
        "event": event,
        "payload": payload,
    }
    with (output_root / "events.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, sort_keys=True, allow_nan=False) + "\n")


def _write_preflight_manifest(output_root: Path, result: dict[str, Any]) -> None:
    """Record reproducibility metadata even when MQ-HW1 blocks before model access."""
    model_config = _validate_model_candidate("Qwen/Qwen2.5-1.5B-Instruct")
    v21 = json.loads(V21_PATH.read_text(encoding="utf-8"))
    packages, env_hash = _environment_inventory()
    artifact = output_root / "hardware_preflight.json"
    payload = {
        "manifest_version": "1.0.0",
        "experiment_id": EXPERIMENT_ID,
        "run_id": RUN_ID,
        "utc_timestamp": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git(["git", "rev-parse", "HEAD"]),
        "uncommitted_diff": bool(_git(["git", "status", "--porcelain"])),
        "dataset_manifest_hashes": {
            _repo_or_absolute(path): _canonical_text_sha256(path)
            for path in (REGISTRY_PATH, MAPPING_PATH, G1_PATH, G2_PATH, HW_PATH, V21_PATH,
                         MODEL_CONFIG_PATH, PROTOCOL_PATH)
        },
        "frozen_input_hash_verification": result.get("frozen_input_hash_verification", {}),
        "model_id": model_config["model_id"], "model_revision": model_config["revision"],
        "tokenizer_revision": model_config["revision"],
        "random_seeds": [v21["seed"]], "hardware_measurements": result["measurements"],
        "python_version": platform.python_version(), "python_executable": sys.executable,
        "python_env_hash": env_hash, "python_packages": packages,
        "command_line": sys.argv, "config_file": _repo_or_absolute(MODEL_CONFIG_PATH),
        "config_hash": _canonical_text_sha256(MODEL_CONFIG_PATH), "model_accessed": False,
        "preflight_decision": result["decision"], "raw_output_path": str(artifact),
        "artifact_paths": {str(artifact): sha256_file(artifact)},
    }
    _write_json(output_root / "preflight_manifest.json", payload)


def _write_failure_manifest(output_root: Path, error: Exception) -> None:
    """Record run identity and hashes for an interrupted/failed model attempt."""
    model_config = json.loads(MODEL_CONFIG_PATH.read_text(encoding="utf-8"))
    v21 = json.loads(V21_PATH.read_text(encoding="utf-8"))
    packages, env_hash = _environment_inventory()
    artifacts = [
        path for path in output_root.iterdir()
        if path.is_file() and path.name != "failure_manifest.json"
    ]
    payload = {
        "manifest_version": "1.0.0", "experiment_id": EXPERIMENT_ID, "run_id": RUN_ID,
        "utc_timestamp": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git(["git", "rev-parse", "HEAD"]),
        "uncommitted_diff": bool(_git(["git", "status", "--porcelain"])),
        "dataset_manifest_hashes": {
            _repo_or_absolute(path): _canonical_text_sha256(path)
            for path in (REGISTRY_PATH, MAPPING_PATH, G1_PATH, G2_PATH, HW_PATH, V21_PATH,
                         MODEL_CONFIG_PATH, PROTOCOL_PATH)
        },
        "frozen_input_hash_verification": {
            key: {
                "expected_frozen_sha256": expected,
                **_text_hashes_with_newline_variants(path),
            }
            for key, path, expected in (
                ("semantic_registry_sha256", REGISTRY_PATH, json.loads(G1_PATH.read_text(encoding="utf-8"))["semantic_registry_sha256"]),
                ("control_mappings_sha256", MAPPING_PATH, json.loads(G1_PATH.read_text(encoding="utf-8"))["control_mappings_sha256"]),
                ("v2_1_config_sha256", V21_PATH, json.loads(G1_PATH.read_text(encoding="utf-8"))["v2_1_config_sha256"]),
                ("model_qualification_protocol", PROTOCOL_PATH, json.loads(G2_PATH.read_text(encoding="utf-8"))["parent_protocol_sha256"]),
            )
        },
        "model_id": model_config["model_id"], "model_revision": model_config["revision"],
        "tokenizer_revision": model_config["revision"], "random_seeds": [v21["seed"]],
        "python_version": platform.python_version(), "python_executable": sys.executable,
        "python_env_hash": env_hash, "python_packages": packages, "hardware": platform.platform(),
        "command_line": sys.argv, "config_file": _repo_or_absolute(MODEL_CONFIG_PATH),
        "config_hash": _canonical_text_sha256(MODEL_CONFIG_PATH),
        "failure": {"exception_type": type(error).__name__, "message": str(error)},
        "raw_output_path": str(output_root / "execution_failure.json"),
        "artifact_paths": {str(path): sha256_file(path) for path in artifacts},
    }
    _write_json(output_root / "failure_manifest.json", payload)


def _assert_frozen_inputs() -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    """Validate checksums, exact development IDs, and frozen case mappings."""
    gate = json.loads(G1_PATH.read_text(encoding="utf-8"))
    hw_gate = json.loads(HW_PATH.read_text(encoding="utf-8"))
    g2_gate = json.loads(G2_PATH.read_text(encoding="utf-8"))
    v21 = json.loads(V21_PATH.read_text(encoding="utf-8"))
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    _validate_model_candidate(hw_gate["candidate_model_id"])
    protocol_hash_diagnostics = _verify_frozen_text_hash(
        PROTOCOL_PATH, g2_gate["parent_protocol_sha256"], "model qualification protocol"
    )
    if g2_gate["minimum_clean_message_rescue_per_direction"] != g2_gate["minimum_attacked_message_induction_per_direction"]:
        raise ValueError("runner requires the protocol's shared rescue/induction threshold")
    if g2_gate["internal_model_interventions"] != "forbidden":
        raise ValueError("MQ-G2 config must forbid internal-model interventions")
    if g2_gate["split_access_policy"]["validation"] != "forbidden" or g2_gate["split_access_policy"]["test"] != "forbidden":
        raise ValueError("MQ-G2 config must keep validation and test closed")
    input_paths = {
        "semantic_registry_sha256": REGISTRY_PATH,
        "control_mappings_sha256": MAPPING_PATH,
        "v2_1_config_sha256": V21_PATH,
    }
    hash_diagnostics = {
        key: _verify_frozen_text_hash(path, gate[key], key)
        for key, path in input_paths.items()
    }
    hash_diagnostics["model_qualification_protocol"] = protocol_hash_diagnostics
    hashes = {key: gate[key] for key in input_paths}
    cases = [case for case in registry["cases"] if case["split"] == "development"]
    if len(cases) != gate["development_case_count"]:
        raise ValueError("development registry count differs from the frozen MQ-G1 gate")
    if any(case["split"] != "development" for case in cases):
        raise PermissionError("qualification runner received a non-development case")
    case_ids = [case["case_id"] for case in cases]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("development registry contains duplicate case IDs")
    for case in cases:
        require_v2_development(case)
    direction_counts = {
        direction: sum(case["attack_direction"] == direction for case in cases)
        for direction in ("A_TO_B", "B_TO_A")
    }
    if any(count != gate["per_class_case_count"] for count in direction_counts.values()):
        raise ValueError(f"development directional counts do not match frozen gate: {direction_counts}")
    return {
        **gate,
        "candidate_model_id": hw_gate["candidate_model_id"],
        "input_hashes": hashes,
        "input_hash_diagnostics": hash_diagnostics,
    }, cases, v21


def run(output_root: Path = OUTPUT_DEFAULT, cache_root: Path | None = None) -> dict[str, Any]:
    """Run one single-attempt CPU-fp32 MQ campaign and persist all raw rows."""
    output_root = output_root.resolve()
    cache_root = (cache_root or (output_root / "hf-cache")).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    cache_root.mkdir(parents=True, exist_ok=True)
    gate, cases, v21 = _assert_frozen_inputs()
    model_config = _validate_model_candidate(gate["candidate_model_id"])
    g2_gate = json.loads(G2_PATH.read_text(encoding="utf-8"))
    if torch.version.cuda is not None or torch.cuda.is_initialized() or torch.cuda.is_available():
        raise RuntimeError("MQ-HW1 requires a CPU-only PyTorch installation and forbids CUDA migration")

    marker = output_root / "model_access_attempt_started.json"
    if not marker.is_file():
        raise RuntimeError("run the frozen MQ-HW1 preflight and pinned snapshot download first")
    marker_payload = json.loads(marker.read_text(encoding="utf-8"))
    if marker_payload.get("state") != "MODEL_FILES_READY":
        raise RuntimeError(f"single-attempt model-access marker is not ready: {marker_payload.get('state')}")
    hw_path = output_root / "hardware_preflight.json"
    if not hw_path.is_file():
        raise RuntimeError("pre-access MQ-HW1 hardware record is missing")
    hw = json.loads(hw_path.read_text(encoding="utf-8"))
    if hw["decision"]["overall"] != "PASS" or hw.get("model_accessed") is not False:
        raise RuntimeError("MQ-HW1 preflight did not pass before model access")
    if marker_payload.get("hardware_preflight_sha256") != sha256_file(hw_path):
        raise RuntimeError("pre-access hardware report differs from the marker")
    if marker_payload.get("model_id") != model_config["model_id"] or marker_payload.get("model_revision") != model_config["revision"]:
        raise RuntimeError("model-access marker does not match the frozen candidate")
    snapshot_manifest_path = Path(marker_payload["snapshot_manifest_path"])
    if not snapshot_manifest_path.is_file():
        raise RuntimeError("pinned model snapshot manifest is missing")
    snapshot_manifest = json.loads(snapshot_manifest_path.read_text(encoding="utf-8"))
    if snapshot_manifest.get("model_id") != model_config["model_id"] or snapshot_manifest.get("resolved_revision") != model_config["revision"]:
        raise RuntimeError("downloaded model snapshot does not match the frozen candidate revision")
    if marker_payload.get("snapshot_manifest_sha256") != sha256_file(snapshot_manifest_path):
        raise RuntimeError("model snapshot manifest hash differs from pre-load marker")
    _verify_snapshot_manifest(snapshot_manifest, cache_root)

    marker_payload = {
        **marker_payload,
        "state": "MODEL_ACCESS_ATTEMPT_STARTED",
        "utc_timestamp": datetime.now(timezone.utc).isoformat(),
        "model_id": model_config["model_id"],
        "model_revision": model_config["revision"],
        "hardware_preflight_sha256": sha256_file(hw_path),
        "one_attempt_policy": gate["candidate_model_id"],
    }
    _write_json(marker, marker_payload)
    _log_event(output_root, "model_loader", "single_load_attempt_started", {
        "model_id": model_config["model_id"],
        "model_revision": model_config["revision"],
        "device": "cpu",
        "dtype": "float32",
    })
    started = time.perf_counter()
    adapter = Qwen2ModelAdapter(
        model_config["model_id"], model_config["revision"], cache_root,
        dtype=torch.float32, device="cpu", local_files_only=True,
        low_cpu_mem_usage=bool(model_config["low_cpu_mem_usage"]),
    )
    torch.set_num_threads(int(model_config.get("cpu_threads", 2)))
    torch.manual_seed(v21["seed"])
    load_error: str | None = None
    try:
        adapter.load()
    except MemoryError as error:
        load_error = f"{type(error).__name__}: {error}"
        marker_payload.update({"state": "BLOCKED_MEMORY_RUNTIME", "load_error": load_error})
        _write_json(marker, marker_payload)
        raise
    except (OSError, RuntimeError) as error:
        load_error = f"{type(error).__name__}: {error}"
        marker_payload.update({"state": "BLOCKED_OR_INCOMPATIBLE", "load_error": load_error})
        _write_json(marker, marker_payload)
        raise
    except Exception as error:
        load_error = f"{type(error).__name__}: {error}"
        marker_payload.update({"state": "BLOCKED_OR_INCOMPATIBLE", "load_error": load_error})
        _write_json(marker, marker_payload)
        raise

    memory_after_load = psutil.virtual_memory().available / 2**30
    _, cgroup_after_load = _cgroup_memory()
    post_state = post_load_memory_state(memory_after_load, json.loads(HW_PATH.read_text(encoding="utf-8")))
    if cgroup_after_load is not None and cgroup_after_load < 2.0:
        post_state = "BLOCKED_AFTER_LOAD"
    if post_state != "READY_FOR_BEHAVIORAL_EXECUTION":
        marker_payload.update({
            "state": post_state,
            "available_ram_after_load_gib": memory_after_load,
            "cgroup_available_after_load_gib": cgroup_after_load,
        })
        _write_json(marker, marker_payload)
        del adapter.model
        raise RuntimeError("MQ-HW1 post-load memory gate failed; behavioral execution was not started")
    _log_event(output_root, "model_loader", "model_loaded", {
        "post_load_state": post_state,
        "available_ram_gib": memory_after_load,
        "cgroup_available_gib": cgroup_after_load,
    })

    if adapter.model is None or adapter.tokenizer is None or adapter.model.training:
        raise RuntimeError("model compatibility check failed: expected loaded eval-mode model and tokenizer")
    if next(adapter.model.parameters()).dtype != torch.float32:
        raise RuntimeError("model compatibility check failed: model parameter dtype is not float32")
    adapter.tokenizer.padding_side = v21["decoder_padding_side"]
    label_ids = validate_label_tokens(adapter.tokenizer)

    # MQ-G1: exact frozen 24-case development set; no hooks, validation, or test access.
    clean_data = [_input(case, str(case["ground_truth_code"])) for case in cases]
    attacked_data = [_input(case, str(case["adversarial_code"])) for case in cases]
    clean_inputs = adapter.tokenize([_sender_prompt(adapter, item) for item in clean_data])
    attacked_inputs = adapter.tokenize([_sender_prompt(adapter, item) for item in attacked_data])
    if clean_inputs["input_ids"].shape != attacked_inputs["input_ids"].shape:
        raise ValueError("paired sender prompts do not align under frozen V2 template")
    prompt_length = clean_inputs["input_ids"].shape[1]
    clean_generated = adapter.generate_uncached(clean_inputs, v21["sender_generation"]["max_new_tokens"])
    attacked_generated = adapter.generate_uncached(attacked_inputs, v21["sender_generation"]["max_new_tokens"])
    clean_codes, clean_ids, clean_full_outputs = _generation_codes(adapter, clean_generated, prompt_length)
    attacked_codes, attacked_ids, attacked_full_outputs = _generation_codes(adapter, attacked_generated, prompt_length)
    clean_messages = [
        MediatorMessage.from_sender_code(str(case["task_id"]), code, v21["mediator_evidence"])
        for case, code in zip(cases, clean_codes, strict=True)
    ]
    attacked_messages = [
        MediatorMessage.from_sender_code(str(case["task_id"]), code, v21["mediator_evidence"])
        for case, code in zip(cases, attacked_codes, strict=True)
    ]
    correct_codes = [str(case["ground_truth_code"]) for case in cases]
    clean_scored = _score_valid_messages(adapter, clean_messages, label_ids, correct_codes)
    attacked_scored = _score_valid_messages(adapter, attacked_messages, label_ids, correct_codes)

    rows: list[dict[str, Any]] = []
    for index, case in enumerate(cases):
        clean_valid = clean_messages[index].valid
        attack_valid = attacked_messages[index].valid
        clean_prediction = clean_scored["predicted"][index]
        attacked_prediction = attacked_scored["predicted"][index]
        clean_correct = bool(clean_valid and clean_prediction == case["ground_truth_code"])
        attack_success = bool(attack_valid and attacked_prediction == case["adversarial_code"])
        rows.append({
            "case_id": case["case_id"], "split": case["split"],
            "direction": case["attack_direction"], "ground_truth_code": case["ground_truth_code"],
            "adversarial_code": case["adversarial_code"],
            "clean_sender_prompt": _sender_prompt(adapter, clean_data[index]),
            "attacked_sender_prompt": _sender_prompt(adapter, attacked_data[index]),
            "sender_prompt_token_ids": [int(token) for token in clean_inputs["input_ids"][index].tolist()],
            "attacked_sender_prompt_token_ids": [int(token) for token in attacked_inputs["input_ids"][index].tolist()],
            "clean_sender_token_ids": clean_ids[index], "attacked_sender_token_ids": attacked_ids[index],
            "clean_sender_full_output": clean_full_outputs[index],
            "attacked_sender_full_output": attacked_full_outputs[index],
            "clean_sender_output": clean_codes[index], "attacked_sender_output": attacked_codes[index],
            "clean_message": asdict(clean_messages[index]) if clean_valid else {
                "valid": False, "raw_sender_output": clean_codes[index],
                "parse_error": clean_messages[index].parse_error,
            },
            "attacked_message": asdict(attacked_messages[index]) if attack_valid else {
                "valid": False, "raw_sender_output": attacked_codes[index],
                "parse_error": attacked_messages[index].parse_error,
            },
            "clean_message_valid": clean_valid, "attacked_message_valid": attack_valid,
            "clean_receiver_code": clean_prediction, "attacked_receiver_code": attacked_prediction,
            "clean_receiver_score": clean_scored["scores"][index],
            "attacked_receiver_score": attacked_scored["scores"][index],
            "clean_receiver_raw_logit_a": clean_scored["raw_a"][index],
            "clean_receiver_raw_logit_b": clean_scored["raw_b"][index],
            "attacked_receiver_raw_logit_a": attacked_scored["raw_a"][index],
            "attacked_receiver_raw_logit_b": attacked_scored["raw_b"][index],
            "clean_receiver_prompt": clean_scored["prompts"][index],
            "attacked_receiver_prompt": attacked_scored["prompts"][index],
            "clean_receiver_prompt_token_ids": clean_scored["input_ids"][index],
            "attacked_receiver_prompt_token_ids": attacked_scored["input_ids"][index],
            "clean_correct": clean_correct, "attack_success": attack_success,
            "eligible": clean_correct and attack_success,
        })
    attempts = [
        BehavioralAttempt(
            case_id=row["case_id"], direction=row["direction"],
            clean_correct=row["clean_correct"], attacked_adversarial=row["attack_success"],
            clean_mediator_valid=row["clean_message_valid"], attack_mediator_valid=row["attacked_message_valid"],
        )
        for row in rows
    ]
    g1 = evaluate_mq_g1(attempts, gate, validation_executions=0, test_executions=0)
    _log_event(output_root, "mq_g1", "qualification_complete", g1)
    _write_json(output_root / "mq_g1_rows.json", rows)
    _write_json(output_root / "mq_g1_result.json", g1)
    marker_payload.update({"state": "MQ_G1_PASS" if g1["overall"] == "PASS" else "MQ_G1_FAIL"})
    _write_json(marker, marker_payload)
    if g1["overall"] != "PASS":
        return _finalize(output_root, model_config, v21, rows, g1, None, started, marker_payload)

    # MQ-G2 only on the exactly enumerated MQ-G1 eligible pairs.
    eligible_indices = [index for index, row in enumerate(rows) if row["eligible"]]
    eligible_ids = {
        direction: [rows[index]["case_id"] for index in eligible_indices if rows[index]["direction"] == direction]
        for direction in ("A_TO_B", "B_TO_A")
    }
    _log_event(output_root, "mq_g2", "eligible_pairs_locked", eligible_ids)
    g2_rows: list[dict[str, Any]] = []
    g2_attempts: list[MessageAttempt] = []
    for direction in ("A_TO_B", "B_TO_A"):
        indices = [index for index in eligible_indices if rows[index]["direction"] == direction]
        for index in indices:
            case = cases[index]
            clean_result = _score_valid_messages(adapter, [clean_messages[index]], label_ids, [correct_codes[index]])
            attacked_result = _score_valid_messages(adapter, [attacked_messages[index]], label_ids, [correct_codes[index]])
            rescue_score = clean_result["scores"][0]
            induction_score = attacked_result["scores"][0]
            rescue_code = clean_result["predicted"][0]
            induction_code = attacked_result["predicted"][0]
            baseline_clean_score = clean_scored["scores"][index]
            baseline_attacked_score = attacked_scored["scores"][index]
            valid_recovery = all(
                value is not None
                for value in (rescue_score, induction_score, baseline_clean_score, baseline_attacked_score)
            )
            recovery: float | None = None
            if valid_recovery:
                denominator = float(baseline_clean_score) - float(baseline_attacked_score)
                if math.isfinite(denominator) and abs(denominator) >= 1e-6:
                    recovery = (float(rescue_score) - float(baseline_attacked_score)) / denominator
                    valid_recovery = math.isfinite(recovery)
                    if not valid_recovery:
                        recovery = None
                else:
                    valid_recovery = False
            rescue_valid = bool(clean_messages[index].valid and rescue_score is not None)
            induction_valid = bool(attacked_messages[index].valid and induction_score is not None)
            rescue_correct = bool(rescue_valid and rescue_code == case["ground_truth_code"])
            induction_adversarial = bool(induction_valid and induction_code == case["adversarial_code"])
            attempt = MessageAttempt(
                case_id=str(case["case_id"]), direction=direction,
                rescue_correct=rescue_correct, induction_adversarial=induction_adversarial,
                normalized_recovery=recovery, rescue_valid=rescue_valid,
                induction_valid=induction_valid, recovery_valid=valid_recovery,
            )
            g2_attempts.append(attempt)
            g2_rows.append({
                "case_id": case["case_id"], "direction": direction,
                "clean_message_sha256": clean_messages[index].sha256(),
                "attacked_message_sha256": attacked_messages[index].sha256(),
                "rescue_receiver_code": rescue_code, "induction_receiver_code": induction_code,
                "rescue_score": rescue_score, "induction_score": induction_score,
                "rescue_prompt": clean_result["prompts"][0],
                "induction_prompt": attacked_result["prompts"][0],
                "rescue_prompt_token_ids": clean_result["input_ids"][0],
                "induction_prompt_token_ids": attacked_result["input_ids"][0],
                "rescue_raw_logit_a": clean_result["raw_a"][0],
                "rescue_raw_logit_b": clean_result["raw_b"][0],
                "induction_raw_logit_a": attacked_result["raw_a"][0],
                "induction_raw_logit_b": attacked_result["raw_b"][0],
                "clean_baseline_score": baseline_clean_score,
                "attacked_baseline_score": baseline_attacked_score,
                "normalized_recovery": recovery, "recovery_valid": valid_recovery,
                "rescue_valid": rescue_valid, "induction_valid": induction_valid,
            })
    g2 = evaluate_mq_g2(
        g2_attempts,
        eligible_ids,
        threshold=float(g2_gate["minimum_clean_message_rescue_per_direction"]),
        minimum_median_recovery=float(
            g2_gate["minimum_median_normalized_clean_message_recovery_per_direction_exclusive"]
        ),
    )
    _log_event(output_root, "mq_g2", "qualification_complete", g2)
    _write_json(output_root / "mq_g2_rows.json", g2_rows)
    _write_json(output_root / "mq_g2_result.json", g2)
    marker_payload.update({"state": "MQ_G2_PASS" if g2["overall"] == "PASS" else "MQ_G2_FAIL"})
    _write_json(marker, marker_payload)
    return _finalize(output_root, model_config, v21, rows, g1, g2, started, marker_payload)


def _finalize(
    output_root: Path,
    model_config: dict[str, Any],
    v21: dict[str, Any],
    rows: list[dict[str, Any]],
    g1: dict[str, Any],
    g2: dict[str, Any] | None,
    started: float,
    marker: dict[str, Any],
) -> dict[str, Any]:
    """Write a run summary and reproducibility manifest for completed gate stages."""
    packages, env_hash = _environment_inventory()
    row_path = output_root / "mq_g1_rows.json"
    g1_path = output_root / "mq_g1_result.json"
    result = {
        "schema_version": "aether.model-qualification.v2",
        "experiment_id": EXPERIMENT_ID,
        "run_id": RUN_ID,
        "utc_timestamp": datetime.now(timezone.utc).isoformat(),
        "model_id": model_config["model_id"], "model_revision": model_config["revision"],
        "tokenizer_id": model_config["model_id"], "tokenizer_revision": model_config["revision"],
        "model_snapshot_manifest_path": marker.get("snapshot_manifest_path"),
        "model_snapshot_manifest_sha256": marker.get("snapshot_manifest_sha256"),
        "execution": {"device": "cpu", "dtype": "float32", "quantized": False, "offload": False},
        "dataset": {"id": "aether-balanced-causal-v2.0.0", "split": "development",
                    "case_ids": [row["case_id"] for row in rows]},
        "seed": v21["seed"], "mq_g1": g1, "mq_g2": g2,
        "decision": "QUALIFIED_FOR_SEPARATE_INSTRUMENTATION_REVIEW"
        if g1["overall"] == "PASS" and g2 is not None and g2["overall"] == "PASS"
        else "FAILED_QUALIFICATION_STOP",
        "model_access_state": marker["state"], "validation_executions": 0, "test_executions": 0,
        "activation_capture": False, "internal_interventions": False,
        "runtime_seconds": time.perf_counter() - started,
        "raw_outputs": [
            str(row_path), str(g1_path), str(output_root / "hardware_preflight.json"),
            str(output_root / "preflight_manifest.json"), str(output_root / "model_access_attempt_started.json"),
        ]
        + ([str(output_root / "mq_g2_rows.json"), str(output_root / "mq_g2_result.json")] if g2 else [])
        + [str(marker["snapshot_manifest_path"]), str(output_root / "events.jsonl")],
    }
    result_path = output_root / "summary.json"
    _write_json(result_path, result)
    packages_path = output_root / "python_environment.json"
    _write_json(packages_path, {"packages": packages, "sha256": env_hash})
    source_paths = [
        Path("paired_trace/run_model_qualification.py"),
        Path("paired_trace/run_foundation.py"),
        Path("paired_trace/balanced_v2.py"),
        Path("paired_trace/schemas.py"),
        Path("paired_trace/model_qualification.py"),
    ]
    artifacts = [path for path in (row_path, g1_path, output_root / "mq_g2_rows.json",
                                    output_root / "mq_g2_result.json", result_path, packages_path,
                                    output_root / "hardware_preflight.json",
                                    output_root / "preflight_manifest.json",
                                    output_root / "model_access_attempt_started.json",
                                    output_root / "events.jsonl",
                                    Path(marker["snapshot_manifest_path"])) if path.is_file()]
    git_commit = _git(["git", "rev-parse", "HEAD"])
    diff = _git(["git", "status", "--porcelain"])
    manifest = {
        "manifest_version": "1.0.0", "experiment_id": EXPERIMENT_ID, "run_id": result["run_id"],
        "utc_timestamp": result["utc_timestamp"], "git_commit": git_commit,
        "uncommitted_diff": bool(diff),
        "dataset_manifest_hashes": {
            _repo_or_absolute(path): _canonical_text_sha256(path)
            for path in (REGISTRY_PATH, MAPPING_PATH, G1_PATH, G2_PATH, HW_PATH, V21_PATH,
                         MODEL_CONFIG_PATH, PROTOCOL_PATH)
        },
        "frozen_input_hash_verification": _assert_frozen_inputs()[0]["input_hash_diagnostics"],
        "model_id": model_config["model_id"], "model_revision": model_config["revision"],
        "tokenizer_revision": model_config["revision"],
        "prompt_versions": {str(path): _canonical_text_sha256(ROOT / path) for path in source_paths},
        "random_seeds": [v21["seed"]],
        "hardware": {"platform": platform.platform(), "cpu_count": os.cpu_count(),
                     "device": "CPU float32", "torch_cuda_available": torch.cuda.is_available()},
        "python_version": platform.python_version(), "python_executable": sys.executable,
        "python_env_hash": env_hash, "python_packages": packages,
        "command_line": sys.argv, "config_file": _repo_or_absolute(MODEL_CONFIG_PATH),
        "config_hash": _canonical_text_sha256(MODEL_CONFIG_PATH),
        "raw_output_path": str(result_path),
        "artifact_paths": {str(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path): sha256_file(path)
                           for path in artifacts},
        "model_snapshot_manifest": marker.get("snapshot_manifest_path"),
        "model_snapshot_manifest_sha256": marker.get("snapshot_manifest_sha256"),
        "timing_seconds": {"total": result["runtime_seconds"]},
    }
    _write_json(output_root / "manifest.json", manifest)
    return result


def main() -> None:
    """Run qualification using the configured output and Hugging Face cache paths."""
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT_DEFAULT)
    parser.add_argument("--cache", type=Path)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    if args.preflight_only:
        cache_root = (args.cache or (args.output.resolve() / "hf-cache")).resolve()
        cache_root.mkdir(parents=True, exist_ok=True)
        frozen_gate, _, _ = _assert_frozen_inputs()
        result = measure_hardware(cache_root)
        result["frozen_input_hash_verification"] = frozen_gate["input_hash_diagnostics"]
        args.output.resolve().mkdir(parents=True, exist_ok=True)
        _write_json(args.output.resolve() / "hardware_preflight.json", result)
        _log_event(args.output.resolve(), "mq_hw1", "preflight_complete", result["decision"])
        _write_preflight_manifest(args.output.resolve(), result)
        print(json.dumps(result, indent=2, allow_nan=False))
        if result["decision"]["overall"] != "PASS":
            raise SystemExit(2)
        return
    try:
        result = run(args.output, args.cache)
    except Exception as error:
        output_root = args.output.resolve()
        output_root.mkdir(parents=True, exist_ok=True)
        _log_event(output_root, "qualification_runner", "execution_failed", {
            "exception_type": type(error).__name__, "message": str(error),
        })
        _write_json(output_root / "execution_failure.json", {
            "utc_timestamp": datetime.now(timezone.utc).isoformat(),
            "exception_type": type(error).__name__,
            "message": str(error),
            "traceback": traceback.format_exc(),
        })
        _write_failure_manifest(output_root, error)
        raise
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
