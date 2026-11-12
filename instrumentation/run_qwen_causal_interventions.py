"""Execute the frozen discovery-only QCI-1.1 real-Qwen intervention campaign."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import subprocess
import sys
import time
import traceback
from typing import Any

import psutil
import torch

from causal.qci_execution import (
    QCICandidate, QueryLedger, assess_candidate, induction_effect, parse_candidate,
    rescue_effect, shuffled_donor_mapping,
)
from experiments.manifest import sha256_file
from instrumentation.adapters import Qwen2ModelAdapter
from paired_trace.balanced_v2 import case_normalized_margin
from paired_trace.metrics import validate_label_tokens
from paired_trace.run_model_qualification import (
    _cgroup_memory, _environment_inventory, _validate_model_candidate,
    _verify_snapshot_manifest, measure_hardware,
)
from paired_trace.schemas import MediatorMessage

ROOT = Path(__file__).resolve().parents[1]
SELECTION_PATH = ROOT / "results/phase1/candidate_selection/qwen15b_qci1/selection.json"
BASE_PROTOCOL_PATH = ROOT / "configs/causal_candidates/qwen_1_5b_dcap1_intervention_v1.json"
EXECUTION_PROTOCOL_PATH = ROOT / "configs/causal_candidates/qwen_1_5b_qci1_execution_v1_1.json"
QUALIFICATION_ROWS_PATH = ROOT / "results/phase1/model_qualification/qwen15b_kaggle_20261110/mq_g1_rows.json"
OUTPUT_DEFAULT = ROOT / "results/phase1/causal_interventions/qwen15b_qci1_discovery"
EXPERIMENT_ID = "P0_cross_20261111_qwen15b_qci1_interventions"
RUN_ID = f"{EXPERIMENT_ID}_seed42"


def _write_json(path: Path, value: Any) -> None:
    """Write strict stable JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def _git(*arguments: str) -> str:
    """Return required Git metadata."""
    return subprocess.run(
        ["git", *arguments], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def _load_inputs() -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], list[QCICandidate]]:
    """Verify frozen selection/protocol inputs and return discovery rows."""
    base = json.loads(BASE_PROTOCOL_PATH.read_text(encoding="utf-8"))
    execution = json.loads(EXECUTION_PROTOCOL_PATH.read_text(encoding="utf-8"))
    if execution.get("status") != "prospectively_frozen_before_any_qci_intervention_execution":
        raise ValueError("QCI execution protocol is not prospectively frozen")
    if sha256_file(SELECTION_PATH) != execution["selection_result_sha256"]:
        raise ValueError("QCI selection differs from the frozen execution input")
    selection = json.loads(SELECTION_PATH.read_text(encoding="utf-8"))
    if selection.get("development_audit_accessed") is not False:
        raise ValueError("QCI selection accessed development audit")
    candidates = [parse_candidate(row) for row in selection["selected"]]
    if len(candidates) != execution["selected_candidate_count"]:
        raise ValueError("QCI selected-candidate count differs from execution protocol")
    rows = json.loads(QUALIFICATION_ROWS_PATH.read_text(encoding="utf-8"))
    by_id = {row["case_id"]: row for row in rows}
    discovery = [by_id[case_id] for case_id in selection["discovery_case_ids"]]
    if any(row["split"] != "development" or not row["eligible"] for row in discovery):
        raise ValueError("QCI discovery includes ineligible or non-development cases")
    if len(discovery) != execution["discovery_case_count"]:
        raise ValueError("QCI discovery-case count differs from execution protocol")
    return base, execution, discovery, candidates


def preflight(output_root: Path, cache_root: Path) -> dict[str, Any]:
    """Verify QCI evidence and hardware before model repository access."""
    base, execution, rows, candidates = _load_inputs()
    hardware = measure_hardware(cache_root)
    packages, environment_hash = _environment_inventory()
    decision = hardware["decision"]["overall"] == "PASS"
    result = {
        "schema_version": "aether.qci-preflight.v1", "experiment_id": EXPERIMENT_ID,
        "run_id": RUN_ID, "utc_timestamp": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git("rev-parse", "HEAD"), "uncommitted_diff": bool(_git("diff", "--name-only")),
        "model_id": base["model_id"], "model_revision": base["model_revision"],
        "tokenizer_revision": base["model_revision"], "random_seeds": [42],
        "python_version": platform.python_version(), "python_executable": sys.executable,
        "python_env_hash": environment_hash, "python_packages": packages,
        "command_line": sys.argv, "config_file": str(EXECUTION_PROTOCOL_PATH.relative_to(ROOT)),
        "config_hash": sha256_file(EXECUTION_PROTOCOL_PATH),
        "dataset_manifest_hashes": {
            "selection": sha256_file(SELECTION_PATH),
            "qualification_rows": sha256_file(QUALIFICATION_ROWS_PATH),
        },
        "discovery_case_ids": [row["case_id"] for row in rows],
        "candidate_ids": [f"{candidate.agent}.{candidate.candidate_id}" for candidate in candidates],
        "validation_executions": 0, "test_executions": 0, "model_accessed": False,
        "hardware": hardware,
        "decision": {"inputs_verified": True, "hardware_pass": decision,
                     "overall": "PASS" if decision else "BLOCKED"},
        "raw_output_path": str(output_root / "qci_preflight.json"),
    }
    _write_json(output_root / "qci_preflight.json", result)
    return result


def _qualified_inputs(
    adapter: Qwen2ModelAdapter, prompt: str, expected_ids: list[int]
) -> dict[str, torch.Tensor]:
    """Validate prompt content and reconstruct exact qualified left padding."""
    tokenized = adapter.tokenize([prompt])
    observed = [int(token) for token in tokenized["input_ids"][0].tolist()]
    pad = adapter.tokenizer.pad_token_id
    if pad is None:
        raise ValueError("QCI tokenizer has no pad token")
    strip = lambda values: values[next((i for i, value in enumerate(values) if value != pad), len(values)):]
    if strip(observed) != strip(expected_ids):
        raise ValueError("QCI prompt tokenization differs from qualified content")
    padding = len(expected_ids) - len(strip(expected_ids))
    device = tokenized["input_ids"].device
    return {
        "input_ids": torch.tensor([expected_ids], dtype=torch.long, device=device),
        "attention_mask": torch.tensor([[0] * padding + [1] * (len(expected_ids) - padding)], dtype=torch.long, device=device),
    }


def _prompt_and_ids(row: dict[str, Any], agent: str, condition: str) -> tuple[str, list[int]]:
    """Return one exact qualified prompt and padded token sequence."""
    if agent == "sender":
        key = "sender_prompt_token_ids" if condition == "clean" else "attacked_sender_prompt_token_ids"
        return row[f"{condition}_sender_prompt"], [int(value) for value in row[key]]
    return row[f"{condition}_receiver_prompt"], [int(value) for value in row[f"{condition}_receiver_prompt_token_ids"]]


def _module_site(adapter: Qwen2ModelAdapter, candidate: QCICandidate) -> Any:
    """Resolve one selected module candidate against the loaded architecture."""
    return next(
        site for site in adapter.identify_components([candidate.layer])
        if site.component_type == candidate.component_type
    )


def _capture_sources(
    adapter: Qwen2ModelAdapter, inputs: dict[str, torch.Tensor], candidates: list[QCICandidate]
) -> dict[str, torch.Tensor]:
    """Capture all selected candidates for one agent/condition in one forward."""
    modules = [_module_site(adapter, candidate) for candidate in candidates if candidate.family == "module"]
    head_layers = sorted({candidate.layer for candidate in candidates if candidate.family == "head"})
    try:
        adapter.install_comprehensive_capture(modules, head_layers)
        adapter.forward(inputs)
        sources: dict[str, torch.Tensor] = {}
        for candidate in candidates:
            if candidate.family == "module":
                sources[candidate.candidate_id] = adapter.activations[
                    f"L{candidate.layer}.{candidate.component_type}"
                ].clone()
            else:
                sources[candidate.candidate_id] = adapter.head_activations[
                    f"L{candidate.layer}.pre_o_proj_heads"
                ][:, :, candidate.head, :].clone()
        return sources
    finally:
        adapter.remove_hooks()


def _install_patch(
    adapter: Qwen2ModelAdapter, candidate: QCICandidate, source: torch.Tensor,
    position: int, sender_generation: bool,
) -> None:
    """Install the exact module/head patch for one QCI execution."""
    if candidate.family == "head":
        adapter.install_head_patch(
            candidate.layer, int(candidate.head), source,
            token_position=position, target_generation_step=0 if sender_generation else None,
        )
    elif sender_generation:
        if position == -1:
            adapter.install_generation_step_patch(_module_site(adapter, candidate), source, target_step=0)
        else:
            adapter.install_generation_position_patch(
                _module_site(adapter, candidate), source, target_step=0, token_position=position
            )
    else:
        adapter.install_activation_patch(_module_site(adapter, candidate), source, [position])


def _normalized_score(logits: torch.Tensor, label_ids: dict[str, int], correct_code: str) -> float:
    """Return the qualification-compatible case-normalized receiver margin."""
    return float(case_normalized_margin(logits, label_ids, [correct_code])[0][0])


def _receiver_execution(
    adapter: Qwen2ModelAdapter, candidate: QCICandidate, source: torch.Tensor | None,
    row: dict[str, Any], target: str, position: int, label_ids: dict[str, int], passive: bool,
) -> tuple[float, dict[str, Any], int]:
    """Run one receiver intervention while keeping its serialized message fixed."""
    prompt, ids = _prompt_and_ids(row, "receiver", target)
    inputs = _qualified_inputs(adapter, prompt, ids)
    try:
        if passive:
            if candidate.family == "head":
                adapter.install_head_capture(candidate.layer)
            else:
                adapter.install_capture_hooks([_module_site(adapter, candidate)])
        else:
            assert source is not None
            _install_patch(adapter, candidate, source, position, False)
        logits = adapter.forward(inputs).logits[:, -1:, :].detach().cpu()
        applications = 0 if passive else adapter.intervention_applications
    finally:
        adapter.remove_hooks()
    score = _normalized_score(logits, label_ids, str(row["ground_truth_code"]))
    return score, {
        "prompt": prompt, "input_token_ids": ids,
        "serialized_message": row[f"{target}_message"],
        "output_code": "A" if float(logits[0, 0, label_ids["A"]]) >= float(logits[0, 0, label_ids["B"]]) else "B",
    }, applications


def _sender_execution(
    adapter: Qwen2ModelAdapter, candidate: QCICandidate, source: torch.Tensor | None,
    row: dict[str, Any], target: str, position: int, label_ids: dict[str, int],
    max_new_tokens: int, passive: bool,
) -> tuple[float | None, dict[str, Any], int, int]:
    """Patch sender, regenerate mediator, then run the receiver on that mediator."""
    prompt, ids = _prompt_and_ids(row, "sender", target)
    inputs = _qualified_inputs(adapter, prompt, ids)
    try:
        if passive:
            if candidate.family == "head":
                adapter.install_head_capture(candidate.layer)
            else:
                adapter.install_capture_hooks([_module_site(adapter, candidate)])
        else:
            assert source is not None
            _install_patch(adapter, candidate, source, position, True)
        generated = adapter.generate_uncached(inputs, max_new_tokens)
        applications = 0 if passive else adapter.intervention_applications
    finally:
        adapter.remove_hooks()
    code = adapter.tokenizer.decode([int(generated[0, len(ids)])], skip_special_tokens=True).strip()
    reference = row["clean_message"]
    message = MediatorMessage.from_sender_code(reference["case_id"], code, reference["evidence"])
    details = {
        "prompt": prompt, "input_token_ids": ids, "sender_output": code,
        "generated_token_ids": [int(value) for value in generated[0, len(ids):].tolist()],
        "mediator_valid": message.valid,
        "serialized_message": message.serialize() if message.valid else None,
        "mediator_sha256": message.sha256() if message.valid else None,
    }
    if not message.valid:
        return None, details, applications, max_new_tokens
    if code == row["clean_sender_output"]:
        receiver_target = "clean"
    elif code == row["attacked_sender_output"]:
        receiver_target = "attacked"
    else:
        return None, details, applications, max_new_tokens
    receiver_prompt, receiver_ids = _prompt_and_ids(row, "receiver", receiver_target)
    receiver_inputs = _qualified_inputs(adapter, receiver_prompt, receiver_ids)
    logits = adapter.forward(receiver_inputs).logits[:, -1:, :].detach().cpu()
    score = _normalized_score(logits, label_ids, str(row["ground_truth_code"]))
    details.update({"receiver_prompt": receiver_prompt, "receiver_input_token_ids": receiver_ids})
    return score, details, applications, max_new_tokens + 1


def _run_one(
    adapter: Qwen2ModelAdapter, candidate: QCICandidate, row: dict[str, Any],
    operator: str, sources: dict[tuple[str, str, str], dict[str, torch.Tensor]],
    donor_map: dict[str, str], by_id: dict[str, dict[str, Any]], label_ids: dict[str, int],
    execution: dict[str, Any], ledger: QueryLedger,
    semantic_donor_maps: dict[str, dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Run one declared candidate/case/operator execution and retain failures."""
    source_condition, target, position, passive = {
        "paired_rescue": ("clean", "attacked", -1, False),
        "paired_induction": ("attacked", "clean", -1, False),
        "shuffled_donor_rescue": ("clean", "attacked", -1, False),
        "same_decision_rescue": ("clean", "attacked", -1, False),
        "same_decision_induction": ("attacked", "clean", -1, False),
        "opposite_decision_rescue": ("clean", "attacked", -1, False),
        "opposite_decision_induction": ("attacked", "clean", -1, False),
        "irrelevant_position_rescue": ("clean", "attacked", int(execution["irrelevant_token_position"]), False),
        "identity_clean_to_clean": ("clean", "clean", -1, False),
        "identity_attacked_to_attacked": ("attacked", "attacked", -1, False),
        "passive_hook": ("attacked", "attacked", -1, True),
    }[operator]
    if operator == "shuffled_donor_rescue":
        donor_id = donor_map[row["case_id"]]
    elif operator.startswith("same_decision_"):
        if semantic_donor_maps is None:
            raise ValueError("QCI semantic donor maps are required")
        donor_id = semantic_donor_maps["same_decision"][row["case_id"]]
    elif operator.startswith("opposite_decision_"):
        if semantic_donor_maps is None:
            raise ValueError("QCI semantic donor maps are required")
        donor_id = semantic_donor_maps["opposite_decision"][row["case_id"]]
    else:
        donor_id = row["case_id"]
    source = None if passive else sources[(donor_id, candidate.agent, source_condition)][candidate.candidate_id]
    forward_charge = 1 if candidate.agent == "receiver" else execution["sender_generation_max_new_tokens"] + 1
    ledger.charge(forward_steps=forward_charge)
    started = time.perf_counter()
    try:
        if candidate.agent == "receiver":
            score, details, applications = _receiver_execution(
                adapter, candidate, source, row, target, position, label_ids, passive
            )
            actual_steps = 1
        else:
            score, details, applications, actual_steps = _sender_execution(
                adapter, candidate, source, row, target, position, label_ids,
                int(execution["sender_generation_max_new_tokens"]), passive,
            )
        clean, attacked = float(row["clean_receiver_score"]), float(row["attacked_receiver_score"])
        effect = None
        status = _execution_status(score, passive, applications)
        if score is not None:
            effect = (
                induction_effect(clean, attacked, score)
                if operator in {"paired_induction", "same_decision_induction", "opposite_decision_induction"}
                else rescue_effect(clean, attacked, score)
            )
        baseline = clean if target == "clean" else attacked
        tolerance = execution["identity_tolerance"]
        noninterference = None
        if operator.startswith("identity_") or passive:
            noninterference = score is not None and math_isclose(score, baseline, tolerance)
        return {
            "candidate_id": f"{candidate.agent}.{candidate.candidate_id}",
            "component_id": candidate.candidate_id, "agent": candidate.agent,
            "family": candidate.family, "layer": candidate.layer, "head": candidate.head,
            "component_type": candidate.component_type, "case_id": row["case_id"],
            "direction": row["direction"], "operator": operator,
            "source_case_id": donor_id, "source_condition": source_condition,
            "target_condition": target, "token_position": position,
            "clean_score": clean, "attacked_score": attacked,
            "intervened_score": score, "normalized_effect": effect,
            "status": status, "noninterference_pass": noninterference,
            "intervention_applications": applications, "hook_cleanup": len(adapter._handles) == 0,
            "model_forward_steps": actual_steps, "runtime_seconds": time.perf_counter() - started,
            "seed": 42, **details,
        }
    except Exception as error:
        adapter.remove_hooks()
        return {
            "candidate_id": f"{candidate.agent}.{candidate.candidate_id}",
            "component_id": candidate.candidate_id, "agent": candidate.agent,
            "family": candidate.family, "layer": candidate.layer, "head": candidate.head,
            "component_type": candidate.component_type, "case_id": row["case_id"],
            "direction": row["direction"], "operator": operator,
            "source_case_id": donor_id, "source_condition": source_condition,
            "target_condition": target, "token_position": position,
            "status": "error", "error_type": type(error).__name__, "error": str(error),
            "normalized_effect": None, "noninterference_pass": False,
            "hook_cleanup": len(adapter._handles) == 0,
            "model_forward_steps": forward_charge, "runtime_seconds": time.perf_counter() - started,
            "seed": 42,
        }


def math_isclose(value: float, reference: float, tolerance: dict[str, float]) -> bool:
    """Apply the frozen identity/passive absolute and relative tolerance."""
    return abs(value - reference) <= float(tolerance["absolute"]) + float(tolerance["relative"]) * abs(reference)


def _execution_status(score: float | None, passive: bool, applications: int) -> str:
    """Classify validity without hiding missing or repeated active patches."""
    if score is None:
        return "invalid_sender_output"
    if not passive and applications != 1:
        return "intervention_application_count_invalid"
    return "ok"


def _run_message_controls(
    adapter: Qwen2ModelAdapter,
    rows: list[dict[str, Any]],
    label_ids: dict[str, int],
    ledger: QueryLedger,
) -> list[dict[str, Any]]:
    """Execute whole-message rescue and induction as the fixed causal positive control."""
    controls: list[dict[str, Any]] = []
    for row in rows:
        clean, attacked = float(row["clean_receiver_score"]), float(row["attacked_receiver_score"])
        for operator, prompt_condition in (
            ("whole_message_rescue", "clean"),
            ("whole_message_induction", "attacked"),
        ):
            ledger.charge(forward_steps=1)
            prompt, ids = _prompt_and_ids(row, "receiver", prompt_condition)
            inputs = _qualified_inputs(adapter, prompt, ids)
            logits = adapter.forward(inputs).logits[:, -1:, :].detach().cpu()
            score = _normalized_score(logits, label_ids, str(row["ground_truth_code"]))
            effect = (
                rescue_effect(clean, attacked, score)
                if operator == "whole_message_rescue"
                else induction_effect(clean, attacked, score)
            )
            controls.append({
                "case_id": row["case_id"], "direction": row["direction"],
                "operator": operator, "source_condition": prompt_condition,
                "clean_score": clean, "attacked_score": attacked,
                "intervened_score": score, "normalized_effect": effect,
                "prompt": prompt, "input_token_ids": ids,
                "serialized_message": row[f"{prompt_condition}_message"],
                "status": "ok", "model_forward_steps": 1, "seed": 42,
            })
    return controls


def run(output_root: Path, cache_root: Path) -> dict[str, Any]:
    """Execute all frozen QCI discovery interventions with one model load."""
    started = time.perf_counter()
    base, execution, rows, candidates = _load_inputs()
    preflight_path, marker_path = output_root / "qci_preflight.json", output_root / "qci_model_access.json"
    if not preflight_path.is_file() or not marker_path.is_file():
        raise RuntimeError("run QCI preflight and snapshot access first")
    preflight_record = json.loads(preflight_path.read_text(encoding="utf-8"))
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    if preflight_record["decision"]["overall"] != "PASS":
        raise RuntimeError("QCI preflight did not pass")
    if marker.get("preflight_sha256") != sha256_file(preflight_path) or marker.get("state") != "MODEL_FILES_READY":
        raise RuntimeError("QCI model-access marker is invalid")
    snapshot_path = Path(marker["snapshot_manifest_path"])
    if sha256_file(snapshot_path) != marker["snapshot_manifest_sha256"]:
        raise RuntimeError("QCI snapshot manifest differs from marker")
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    _verify_snapshot_manifest(snapshot, cache_root)
    if torch.version.cuda is not None or torch.cuda.is_available():
        raise RuntimeError("QCI-1 requires the qualified CPU-only condition")
    torch.manual_seed(42); torch.set_num_threads(2)
    model = _validate_model_candidate(base["model_id"])
    adapter = Qwen2ModelAdapter(
        model["model_id"], model["revision"], cache_root, dtype=torch.float32,
        device="cpu", local_files_only=True, low_cpu_mem_usage=True,
    )
    adapter.load(); adapter.tokenizer.padding_side = "left"
    available = psutil.virtual_memory().available / 2**30
    _limit, cgroup_available = _cgroup_memory()
    if min(value for value in (available, cgroup_available) if value is not None) < 2.0:
        raise MemoryError("post-load memory is below QCI minimum")
    label_ids = validate_label_tokens(adapter.tokenizer)
    by_id = {row["case_id"]: row for row in rows}
    donor_map = shuffled_donor_mapping(rows)
    sources: dict[tuple[str, str, str], dict[str, torch.Tensor]] = {}
    forward_steps = 0
    for index, row in enumerate(rows, start=1):
        print(f"QCI source capture [{index}/{len(rows)}] {row['case_id']}", flush=True)
        for agent in ("sender", "receiver"):
            selected = [candidate for candidate in candidates if candidate.agent == agent]
            for condition in ("clean", "attacked"):
                prompt, ids = _prompt_and_ids(row, agent, condition)
                inputs = _qualified_inputs(adapter, prompt, ids)
                sources[(row["case_id"], agent, condition)] = _capture_sources(adapter, inputs, selected)
                forward_steps += 1
    ledger = QueryLedger(
        int(execution["maximum_discovery_intervention_executions"]),
        int(execution["maximum_total_model_forward_steps"]),
        forward_steps=forward_steps,
    )
    operators = list(execution["per_candidate_discovery_operators"])
    raw_path = output_root / "raw_interventions.jsonl"
    all_results: list[dict[str, Any]] = []
    output_root.mkdir(parents=True, exist_ok=True)
    with raw_path.open("w", encoding="utf-8") as stream:
        total = len(candidates) * len(rows) * len(operators)
        completed = 0
        for candidate in candidates:
            for row in rows:
                for operator in operators:
                    result = _run_one(
                        adapter, candidate, row, operator, sources, donor_map, by_id,
                        label_ids, execution, ledger,
                    )
                    all_results.append(result)
                    stream.write(json.dumps(result, sort_keys=True, allow_nan=False) + "\n"); stream.flush()
                    completed += 1
                    print(f"QCI [{completed}/{total}] {candidate.candidate_id} {row['case_id']} {operator} status={result['status']}", flush=True)
    message_controls = _run_message_controls(adapter, rows, label_ids, ledger)
    if len(message_controls) != execution["message_positive_control_executions"]:
        raise ValueError("QCI message-positive-control count differs from protocol")
    assessments = []
    for candidate in candidates:
        assessments.append(assess_candidate(
            [row for row in all_results
             if row["candidate_id"] == f"{candidate.agent}.{candidate.candidate_id}"],
            base["support_thresholds"],
        ))
    supported = [row["candidate_id"] for row in assessments if row["status"] == "supported"]
    summary = {
        "schema_version": "aether.qci-discovery.v1", "experiment_id": EXPERIMENT_ID,
        "run_id": RUN_ID, "utc_timestamp": datetime.now(timezone.utc).isoformat(),
        "model_id": base["model_id"], "model_revision": base["model_revision"],
        "protocol_hash": sha256_file(EXECUTION_PROTOCOL_PATH), "selection_hash": sha256_file(SELECTION_PATH),
        "discovery_case_ids": [row["case_id"] for row in rows],
        "development_audit_executions": 0, "validation_executions": 0, "test_executions": 0,
        "candidate_count": len(candidates), "candidate_execution_count": len(all_results),
        "invalid_or_error_count": sum(row["status"] != "ok" for row in all_results),
        "supported_candidates": supported, "assessment_outcome": "supported_candidates_found" if supported else "no_internal_candidate_passed",
        "query_ledger": asdict(ledger), "runtime_seconds": time.perf_counter() - started,
        "next_state": "READY_FOR_FROZEN_DEVELOPMENT_AUDIT" if supported else "STOP_INTERNAL_CAUSAL_CLAIM",
        "claim_boundary": base["claim_boundary"],
    }
    summary["message_positive_control_count"] = len(message_controls)
    message_path = output_root / "message_positive_controls.json"
    assessments_path, summary_path = output_root / "candidate_assessments.json", output_root / "summary.json"
    _write_json(message_path, message_controls)
    _write_json(assessments_path, assessments); _write_json(summary_path, summary)
    marker["state"] = "QCI_DISCOVERY_COMPLETE"; marker["utc_timestamp"] = summary["utc_timestamp"]
    _write_json(marker_path, marker)
    packages, environment_hash = _environment_inventory()
    manifest = {
        "manifest_version": "1.0.0", "experiment_id": EXPERIMENT_ID, "run_id": RUN_ID,
        "utc_timestamp": summary["utc_timestamp"], "git_commit": _git("rev-parse", "HEAD"),
        "uncommitted_diff": bool(_git("diff", "--name-only")),
        "dataset_manifest_hashes": {"selection": sha256_file(SELECTION_PATH), "qualification_rows": sha256_file(QUALIFICATION_ROWS_PATH)},
        "model_id": base["model_id"], "model_revision": base["model_revision"],
        "tokenizer_revision": base["model_revision"], "prompt_versions": {"qualification": "V2.1"},
        "random_seeds": [42], "hardware": platform.platform(), "python_env_hash": environment_hash,
        "python_packages": packages, "command_line": sys.argv,
        "config_file": str(EXECUTION_PROTOCOL_PATH.relative_to(ROOT)), "raw_output_path": str(raw_path),
        "artifact_paths": {str(path): sha256_file(path) for path in (raw_path, message_path, assessments_path, summary_path, preflight_path, marker_path, snapshot_path)},
    }
    _write_json(output_root / "manifest.json", manifest)
    return summary


def main() -> None:
    """Run preflight or the frozen QCI intervention campaign."""
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
        failure_path = arguments.output / "execution_failure.json"
        failure = {
            "schema_version": "aether.qci-failure.v1",
            "experiment_id": EXPERIMENT_ID, "run_id": RUN_ID,
            "utc_timestamp": datetime.now(timezone.utc).isoformat(),
            "exception_type": type(error).__name__, "message": str(error),
            "traceback": traceback.format_exc(),
            "git_commit": _git("rev-parse", "HEAD"),
            "uncommitted_diff": bool(_git("diff", "--name-only")),
            "model_id": json.loads(BASE_PROTOCOL_PATH.read_text(encoding="utf-8"))["model_id"],
            "model_revision": json.loads(BASE_PROTOCOL_PATH.read_text(encoding="utf-8"))["model_revision"],
            "tokenizer_revision": json.loads(BASE_PROTOCOL_PATH.read_text(encoding="utf-8"))["model_revision"],
            "random_seeds": [42], "config_file": str(EXECUTION_PROTOCOL_PATH.relative_to(ROOT)),
            "config_hash": sha256_file(EXECUTION_PROTOCOL_PATH),
            "selection_hash": sha256_file(SELECTION_PATH),
            "validation_executions": 0, "test_executions": 0,
        }
        _write_json(failure_path, failure)
        packages, environment_hash = _environment_inventory()
        _write_json(arguments.output / "failure_manifest.json", {
            "manifest_version": "1.0.0", "experiment_id": EXPERIMENT_ID,
            "run_id": RUN_ID, "utc_timestamp": failure["utc_timestamp"],
            "git_commit": failure["git_commit"], "uncommitted_diff": failure["uncommitted_diff"],
            "dataset_manifest_hashes": {"selection": failure["selection_hash"]},
            "model_id": failure["model_id"], "model_revision": failure["model_revision"],
            "tokenizer_revision": failure["tokenizer_revision"], "prompt_versions": {"qualification": "V2.1"},
            "random_seeds": [42], "hardware": platform.platform(),
            "python_env_hash": environment_hash, "python_packages": packages,
            "command_line": sys.argv, "config_file": failure["config_file"],
            "raw_output_path": str(failure_path),
            "artifact_paths": {str(failure_path): sha256_file(failure_path)},
        })
        raise


if __name__ == "__main__":
    main()
