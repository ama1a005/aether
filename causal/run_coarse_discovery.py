"""Development-only real-Qwen coarse sender/receiver causal scan."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import time

import numpy as np
import torch

from causal.development_baselines import QueryBudget, clean_utility, deterministic_matched_controls
from causal.evidence import CausalEdgeEvidence
from experiments.manifest import sha256_file
from instrumentation.adapters import Qwen2ModelAdapter
from paired_trace.metrics import escalation_margin, mediation_recovery, validate_label_tokens
from paired_trace.run_foundation import _cases, _input, _sender_prompt, _receiver_prompt
from paired_trace.schemas import MediatorMessage
from paired_trace.splits import frozen_splits, require_development, split_hash

REGISTRY_PATH = Path("configs/causal_candidates/qwen2_5_0_5b_phase1_coarse.json")
MODEL_PATH = Path("configs/models/model_registry.json")
OUTPUT_DIR = Path("results/phase1/causal_discovery")


def _capture(adapter: Qwen2ModelAdapter, inputs: dict[str, torch.Tensor], sites: list[object]) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
    try:
        adapter.install_capture_hooks(sites)
        logits = adapter.forward(inputs).logits
        return logits, {key: value.clone() for key, value in adapter.activations.items()}
    finally:
        adapter.remove_hooks()


def _codes(scores: torch.Tensor) -> list[str]:
    return ["A" if value >= 0 else "B" for value in scores]


def _stats(values: list[float]) -> dict[str, object]:
    array = np.asarray(values, dtype=float)
    rng = np.random.default_rng(42)
    bootstrap = np.asarray([rng.choice(array, len(array), replace=True).mean() for _ in range(2000)])
    return {"N": len(values), "mean": float(array.mean()), "median": float(np.median(array)), "std": float(array.std()), "min": float(array.min()), "max": float(array.max()), "bootstrap_mean_95_ci": [float(np.quantile(bootstrap, 0.025)), float(np.quantile(bootstrap, 0.975))], "values": values}


def _score_messages(adapter: Qwen2ModelAdapter, messages: list[MediatorMessage], label_ids: dict[str, int]) -> tuple[torch.Tensor, dict[str, torch.Tensor], dict[str, torch.Tensor]]:
    prompts = [_receiver_prompt(adapter, message.serialize()) for message in messages]
    inputs = adapter.tokenize(prompts)
    logits = adapter.forward(inputs).logits
    return escalation_margin(logits, label_ids), inputs, {}


def main() -> None:
    """Run every predeclared coarse site on the frozen development pairs."""
    started = time.perf_counter()
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    if not registry.get("frozen_before_scan") or registry["scope"] != "development_only":
        raise PermissionError("candidate registry is not frozen development-only")
    model_meta = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
    adapter = Qwen2ModelAdapter(model_meta["local_path"], model_meta["model_revision"], Path(model_meta["cache_dir"]), torch.float32, "cpu", True)
    adapter.load()
    if len(adapter.model.model.layers) != registry["architecture_layer_count"]:
        raise ValueError("model architecture does not match frozen registry")
    sites = adapter.identify_components(registry["layers"])
    label_ids = validate_label_tokens(adapter.tokenizer)
    all_cases = _cases()
    splits = frozen_splits([str(case["pair_id"]) for case in all_cases])
    cases = [case for case in all_cases if case["pair_id"] in splits["development"]]
    for case in cases:
        require_development(str(case["pair_id"]), splits)
    pair_ids = [str(case["pair_id"]) for case in cases]
    clean_sender_prompts = [_sender_prompt(adapter, _input(case, "A")) for case in cases]
    attacked_sender_prompts = [_sender_prompt(adapter, _input(case, "B")) for case in cases]
    clean_sender_inputs = adapter.tokenize(clean_sender_prompts)
    attacked_sender_inputs = adapter.tokenize(attacked_sender_prompts)
    if clean_sender_inputs["input_ids"].shape != attacked_sender_inputs["input_ids"].shape:
        raise ValueError("sender inputs are not structurally aligned")
    budget = QueryBudget()
    _, clean_sender_acts = _capture(adapter, clean_sender_inputs, sites)
    _, attacked_sender_acts = _capture(adapter, attacked_sender_inputs, sites)
    budget.sender_forwards += 2
    prompt_length = clean_sender_inputs["input_ids"].shape[1]
    clean_generated = adapter.generate(clean_sender_inputs, 1)
    attacked_generated = adapter.generate(attacked_sender_inputs, 1)
    budget.sender_generations += 2
    clean_outputs = [adapter.tokenizer.decode(row[prompt_length:], skip_special_tokens=True) for row in clean_generated]
    attacked_outputs = [adapter.tokenizer.decode(row[prompt_length:], skip_special_tokens=True) for row in attacked_generated]
    clean_messages = [MediatorMessage.from_sender_code(str(case["task_id"]), output, "authoritative ECG tool analysis") for case, output in zip(cases, clean_outputs)]
    attacked_messages = [MediatorMessage.from_sender_code(str(case["task_id"]), output, "authoritative ECG tool analysis") for case, output in zip(cases, attacked_outputs)]
    clean_receiver_prompts = [_receiver_prompt(adapter, message.serialize()) for message in clean_messages]
    attacked_receiver_prompts = [_receiver_prompt(adapter, message.serialize()) for message in attacked_messages]
    clean_receiver_inputs = adapter.tokenize(clean_receiver_prompts)
    attacked_receiver_inputs = adapter.tokenize(attacked_receiver_prompts)
    if clean_receiver_inputs["input_ids"].shape != attacked_receiver_inputs["input_ids"].shape:
        raise ValueError("receiver inputs are not structurally aligned")
    clean_logits, clean_receiver_acts = _capture(adapter, clean_receiver_inputs, sites)
    attacked_logits, attacked_receiver_acts = _capture(adapter, attacked_receiver_inputs, sites)
    budget.receiver_forwards += 2
    clean_scores = escalation_margin(clean_logits, label_ids)
    attacked_scores = escalation_margin(attacked_logits, label_ids)

    sender_rows = []
    sender_scan_started = time.perf_counter()
    sender_position = clean_sender_inputs["input_ids"].shape[1] - 1
    for site in sites:
        candidate_started = time.perf_counter()
        try:
            adapter.install_activation_patch(site, clean_sender_acts[site.component_id], [sender_position])
            generated = adapter.generate(attacked_sender_inputs, 1)
            applications = adapter.intervention_applications
        finally:
            adapter.remove_hooks()
        budget.sender_generations += 1
        outputs = [adapter.tokenizer.decode(row[prompt_length:], skip_special_tokens=True) for row in generated]
        messages = [MediatorMessage.from_sender_code(str(case["task_id"]), output, "authoritative ECG tool analysis") for case, output in zip(cases, outputs)]
        scores, _, _ = _score_messages(adapter, messages, label_ids)
        budget.receiver_forwards += 1
        message_recovery = [float(message.decision_code == clean_messages[i].decision_code) for i, message in enumerate(messages)]
        downstream = [mediation_recovery(float(clean_scores[i]), float(attacked_scores[i]), float(scores[i])) for i in range(len(cases))]
        sender_rows.append({"candidate_id": f"sender.{site.component_id}", "component_type": site.component_type, "layer": site.layer, "association_norm": float((clean_sender_acts[site.component_id][:, -1] - attacked_sender_acts[site.component_id][:, -1]).norm(dim=-1).mean()), "applications": applications, "message_changed_count": sum(message.sha256() != attacked_messages[i].sha256() for i, message in enumerate(messages)), "decision_recovery": _stats(message_recovery), "downstream_recovery": _stats(downstream), "outputs": outputs, "runtime_seconds": time.perf_counter() - candidate_started})
    sender_runtime = time.perf_counter() - sender_scan_started

    receiver_rows = []
    receiver_scan_started = time.perf_counter()
    receiver_position = clean_receiver_inputs["input_ids"].shape[1] - 1
    for site in sites:
        candidate_started = time.perf_counter()
        try:
            adapter.install_activation_patch(site, clean_receiver_acts[site.component_id], [receiver_position])
            logits = adapter.forward(attacked_receiver_inputs).logits
            applications = adapter.intervention_applications
        finally:
            adapter.remove_hooks()
        budget.receiver_forwards += 1
        scores = escalation_margin(logits, label_ids)
        recovery = [mediation_recovery(float(clean_scores[i]), float(attacked_scores[i]), float(scores[i])) for i in range(len(cases))]
        raw = [float(scores[i] - attacked_scores[i]) for i in range(len(cases))]
        receiver_rows.append({"candidate_id": f"receiver.{site.component_id}", "component_type": site.component_type, "layer": site.layer, "association_norm": float((clean_receiver_acts[site.component_id][:, -1] - attacked_receiver_acts[site.component_id][:, -1]).norm(dim=-1).mean()), "applications": applications, "fixed_message_sha256": [message.sha256() for message in attacked_messages], "recovery": _stats(recovery), "raw_effect": _stats(raw), "patched_codes": _codes(scores), "runtime_seconds": time.perf_counter() - candidate_started})
    receiver_runtime = time.perf_counter() - receiver_scan_started

    sender_ranked = sorted(sender_rows, key=lambda row: (row["decision_recovery"]["median"], row["downstream_recovery"]["median"]), reverse=True)
    receiver_ranked = sorted(receiver_rows, key=lambda row: row["recovery"]["median"], reverse=True)
    top_k = registry["top_k_refinement"]
    sender_top = [row["candidate_id"] for row in sender_ranked[:top_k]]
    receiver_top = [row["candidate_id"] for row in receiver_ranked[:top_k]]
    sender_controls = deterministic_matched_controls([row["candidate_id"] for row in sender_rows], sender_top, registry["matched_control_seeds"])
    receiver_controls = deterministic_matched_controls([row["candidate_id"] for row in receiver_rows], receiver_top, registry["matched_control_seeds"])
    sender_supported = [row for row in sender_rows if row["decision_recovery"]["mean"] > 0 and row["message_changed_count"] > 0]
    receiver_supported = [row for row in receiver_rows if row["recovery"]["median"] > 0 and row["raw_effect"]["mean"] > 0]
    for row in sender_supported:
        site = next(site for site in sites if f"sender.{site.component_id}" == row["candidate_id"])
        utility_started = time.perf_counter()
        try:
            adapter.install_activation_patch(site, clean_sender_acts[site.component_id], [sender_position])
            generated = adapter.generate(clean_sender_inputs, 1)
        finally:
            adapter.remove_hooks()
        budget.sender_generations += 1
        outputs = [adapter.tokenizer.decode(item[prompt_length:], skip_special_tokens=True) for item in generated]
        utility_messages = [MediatorMessage.from_sender_code(str(case["task_id"]), output, "authoritative ECG tool analysis") for case, output in zip(cases, outputs)]
        utility_scores, _, _ = _score_messages(adapter, utility_messages, label_ids)
        budget.receiver_forwards += 1
        row["clean_utility"] = clean_utility(clean_outputs, outputs, [float(value) for value in clean_scores], [float(value) for value in utility_scores], sum(not message.valid for message in utility_messages), time.perf_counter() - utility_started)
    for row in receiver_supported:
        site = next(site for site in sites if f"receiver.{site.component_id}" == row["candidate_id"])
        utility_started = time.perf_counter()
        try:
            adapter.install_activation_patch(site, clean_receiver_acts[site.component_id], [receiver_position])
            logits = adapter.forward(clean_receiver_inputs).logits
        finally:
            adapter.remove_hooks()
        budget.receiver_forwards += 1
        scores = escalation_margin(logits, label_ids)
        row["clean_utility"] = clean_utility(_codes(clean_scores), _codes(scores), [float(value) for value in clean_scores], [float(value) for value in scores], 0, time.perf_counter() - utility_started)
    evidence = []
    for row in sender_rows:
        supported = row in sender_supported
        evidence.append(CausalEdgeEvidence(f"{row['candidate_id']}->message.decision_code", row["candidate_id"], "message.decision_code", "sender_internal", "message_field", "activation_intervention", "paired_clean_patch", tuple(pair_ids), len(pair_ids), len(pair_ids), tuple(row["downstream_recovery"]["values"]), row["downstream_recovery"]["median"], "toward_clean" if supported else "no_supported_clean_shift", None, ("sender_scan.json",), ("manifest.json",), "development", "supported" if supported else "rejected"))
    for row in receiver_rows:
        supported = row in receiver_supported
        evidence.append(CausalEdgeEvidence(f"{row['candidate_id']}->outcome", row["candidate_id"], "receiver.outcome", "receiver_internal", "outcome", "activation_intervention", "paired_clean_patch_fixed_message", tuple(pair_ids), len(pair_ids), len(pair_ids), tuple(row["recovery"]["values"]), row["recovery"]["median"], "toward_clean" if supported else "no_supported_clean_shift", None, ("receiver_scan.json",), ("manifest.json",), "development", "supported" if supported else "rejected"))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    sender_path = OUTPUT_DIR / "sender_scan.json"
    receiver_path = OUTPUT_DIR / "receiver_scan.json"
    evidence_path = OUTPUT_DIR / "dcmg_evidence.json"
    sender_path.write_text(json.dumps(sender_rows, indent=2), encoding="utf-8")
    receiver_path.write_text(json.dumps(receiver_rows, indent=2), encoding="utf-8")
    evidence_path.write_text(json.dumps([edge.to_dict() for edge in evidence], indent=2), encoding="utf-8")
    message_summary = json.loads(Path("results/phase1/paired_real/summary.json").read_text(encoding="utf-8"))["message_interventions"]
    summary = {"result_state": "DEV", "evaluation_origin": "aether_positive_control", "split": "development", "split_hash": split_hash(splits), "validation_test_accessed": False, "candidate_registry_hash": sha256_file(REGISTRY_PATH), "candidate_count_per_role": len(sites), "sender_supported": [row["candidate_id"] for row in sender_supported], "receiver_supported": [row["candidate_id"] for row in receiver_supported], "top_k": {"sender": sender_top, "receiver": receiver_top}, "matched_controls": {"sender": sender_controls, "receiver": receiver_controls, "seeds": registry["matched_control_seeds"]}, "baselines": {"message_only": message_summary, "trace_level_clean_message_replay_recovery": message_summary["clean_message_rescue_mean_recovery"], "receiver_only_best": receiver_ranked[0]}, "preliminary_incremental_value": {"distributed_path_supported": bool(sender_supported and receiver_supported), "claim": "development candidate evidence only; message-only remains the strongest simple baseline"}, "query_counts": asdict(budget), "total_queries": budget.total, "runtimes": {"sender_scan_seconds": sender_runtime, "receiver_scan_seconds": receiver_runtime, "total_seconds": time.perf_counter() - started}, "utc_timestamp": datetime.now(timezone.utc).isoformat()}
    summary_path = OUTPUT_DIR / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    artifacts = {str(path): sha256_file(path) for path in (sender_path, receiver_path, evidence_path, summary_path)}
    manifest = {"manifest_version": "1.0.0", "experiment_id": "P0_cross_20261014_coarse_discovery_0", "result_state": "DEV", "git_commit": "b531b7d", "model_id": model_meta["model_id"], "model_revision": model_meta["model_revision"], "candidate_registry": str(REGISTRY_PATH), "candidate_registry_hash": sha256_file(REGISTRY_PATH), "split": "development", "split_hash": split_hash(splits), "pair_ids": pair_ids, "random_seeds": registry["matched_control_seeds"], "artifacts": artifacts, "query_counts": asdict(budget)}
    (OUTPUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
