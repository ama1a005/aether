"""Execute the frozen development-only causal-specificity protocol."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import random
import time

import numpy as np
import torch

from causal.development_baselines import QueryBudget
from causal.evidence import CausalEdgeEvidence
from causal.run_coarse_discovery import _capture, _codes, _score_messages, _stats
from experiments.manifest import sha256_file
from instrumentation.adapters import Qwen2ModelAdapter
from paired_trace.metrics import escalation_margin, mediation_recovery, validate_label_tokens
from paired_trace.run_foundation import _cases, _input, _receiver_prompt, _sender_prompt
from paired_trace.schemas import MediatorMessage
from paired_trace.splits import frozen_splits, require_development, split_hash

CONFIG_PATH = Path("configs/causal_candidates/qwen2_5_0_5b_specificity_hardening.json")
PROTOCOL_PATH = Path("docs/CAUSAL_SPECIFICITY_PROTOCOL.md")
MODEL_PATH = Path("configs/models/model_registry.json")
OUTPUT_DIR = Path("results/phase1/causal_specificity")


def _aligned_positions(clean: torch.Tensor, attacked: torch.Tensor) -> dict[str, int]:
    if clean.shape != attacked.shape:
        raise ValueError("paired inputs must have equal shapes")
    differing = []
    for row in range(clean.shape[0]):
        positions = torch.where(clean[row] != attacked[row])[0].tolist()
        if not positions:
            raise ValueError("paired inputs contain no differing evidence token")
        differing.append(positions[0])
    if len(set(differing)) != 1:
        raise ValueError("first differing position is not stable across pairs")
    if not torch.equal(clean[:, 1], attacked[:, 1]):
        raise ValueError("predeclared irrelevant token is not structurally equal")
    return {"decision": clean.shape[1] - 1, "evidence": differing[0], "irrelevant": 1}


def _recovery(clean: torch.Tensor, attacked: torch.Tensor, intervened: torch.Tensor) -> list[float]:
    return [mediation_recovery(float(clean[i]), float(attacked[i]), float(intervened[i])) for i in range(len(clean))]


def _induction(clean: torch.Tensor, attacked: torch.Tensor, intervened: torch.Tensor) -> list[float]:
    return [mediation_recovery(float(attacked[i]), float(clean[i]), float(intervened[i])) for i in range(len(clean))]


def _fraction(values: list[float], threshold: float = 0.25) -> float:
    return sum(value > threshold for value in values) / len(values)


def _sender_patch(adapter: Qwen2ModelAdapter, site: object, source: torch.Tensor, target: dict[str, torch.Tensor], position: int, prompt_length: int, cases: list[dict[str, object]], label_ids: dict[str, int], budget: QueryBudget) -> dict[str, object]:
    started = time.perf_counter()
    try:
        adapter.install_activation_patch(site, source, [position])
        generated = adapter.generate(target, 1)
        applications = adapter.intervention_applications
    finally:
        adapter.remove_hooks()
    budget.sender_generations += 1
    outputs = [adapter.tokenizer.decode(row[prompt_length:], skip_special_tokens=True) for row in generated]
    messages = [MediatorMessage.from_sender_code(str(case["task_id"]), output, "authoritative ECG tool analysis") for case, output in zip(cases, outputs)]
    scores, _, _ = _score_messages(adapter, messages, label_ids)
    budget.receiver_forwards += 1
    return {"outputs": outputs, "messages": messages, "scores": scores, "applications": applications, "runtime_seconds": time.perf_counter() - started}


def _receiver_patch(adapter: Qwen2ModelAdapter, site: object, source: torch.Tensor, target: dict[str, torch.Tensor], position: int, label_ids: dict[str, int], budget: QueryBudget) -> dict[str, object]:
    started = time.perf_counter()
    try:
        adapter.install_activation_patch(site, source, [position])
        logits = adapter.forward(target).logits
        applications = adapter.intervention_applications
    finally:
        adapter.remove_hooks()
    budget.receiver_forwards += 1
    return {"scores": escalation_margin(logits, label_ids), "applications": applications, "runtime_seconds": time.perf_counter() - started}


def _sample_controls(config: dict[str, object], sites: list[object]) -> list[dict[str, object]]:
    selected = {f"sender.{site}" for site in config["sender_candidates"]} | {f"receiver.{site}" for site in config["receiver_candidates"]}
    controls = [{"seed": 101, "role": "sender", "site": "L23.block_output", "retained_prior_strong_control": True}]
    used = {"sender.L23.block_output"}
    templates = [("sender", "block_output"), ("sender", "attention_output"), ("receiver", "block_output"), ("receiver", "attention_output")]
    for offset, seed in enumerate(config["matched_random_controls"]["seeds"][1:]):
        role, component = templates[offset % len(templates)]
        pool = sorted(f"{role}.{site.component_id}" for site in sites if site.component_type == component and f"{role}.{site.component_id}" not in selected and f"{role}.{site.component_id}" not in used)
        if not pool:
            pool = sorted(f"{role}.{site.component_id}" for site in sites if site.component_type == component and f"{role}.{site.component_id}" not in selected)
        identity = pool[random.Random(seed).randrange(len(pool))]
        used.add(identity)
        controls.append({"seed": seed, "role": role, "site": identity.split(".", 1)[1], "retained_prior_strong_control": False})
    return controls


def _evaluate_candidate(
    row: dict[str, object],
    role: str,
    control_results: list[dict[str, object]],
    position_results: dict[str, dict[str, object]],
    config: dict[str, object],
) -> dict[str, object]:
    """Apply the frozen strong-support criteria to one candidate result."""
    criteria = config["strong_support_criteria"]
    matching = [
        item["rescue"]["median"]
        for item in control_results
        if item["role"] == role and item["component_type"] == row["component_type"]
    ]
    control_median = float(np.median(matching)) if matching else 0.0
    is_position_top = row["candidate_id"] == (
        f"{role}.{config['position_specificity_candidates'][role]}"
    )
    irrelevant = position_results[role]["irrelevant"]["median"] if is_position_top else None
    checks = {
        "median_rescue": row["rescue"]["median"] >= criteria["median_rescue_minimum"],
        "rescue_consistency": _fraction(row["rescue"]["values"])
        >= criteria["rescue_fraction_above_0_25_minimum"],
        "median_induction": row["induction"]["median"] >= criteria["median_induction_minimum"],
        "induction_consistency": _fraction(row["induction"]["values"])
        >= criteria["induction_fraction_above_0_25_minimum"],
        "control_separation": row["rescue"]["median"] - control_median
        >= criteria["matched_control_median_separation_minimum"],
        "shuffled_separation": row["rescue"]["median"] - row["shuffled_rescue"]["median"]
        >= criteria["shuffled_activation_separation_minimum"],
        "position_separation": True
        if irrelevant is None
        else row["rescue"]["median"] - irrelevant
        >= criteria["irrelevant_position_separation_minimum"],
    }
    return {
        "candidate_id": row["candidate_id"],
        "checks": checks,
        "matched_control_median": control_median,
        "irrelevant_position_median": irrelevant,
        "status": "supported" if all(checks.values()) else "rejected",
        "reasons": [name for name, passed in checks.items() if not passed],
    }


def main() -> None:
    """Run hardening without accessing validation or test executions."""
    started = time.perf_counter()
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if config["scope"] != "development_only":
        raise PermissionError("hardening is development-only")
    model_meta = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
    adapter = Qwen2ModelAdapter(model_meta["local_path"], model_meta["model_revision"], Path(model_meta["cache_dir"]), torch.float32, "cpu", True)
    adapter.load()
    label_ids = validate_label_tokens(adapter.tokenizer)
    all_cases = _cases()
    splits = frozen_splits([str(case["pair_id"]) for case in all_cases])
    cases = [case for case in all_cases if case["pair_id"] in splits["development"]]
    for case in cases:
        require_development(str(case["pair_id"]), splits)
    pair_ids = [str(case["pair_id"]) for case in cases]
    layers = sorted({int(site.split(".")[0][1:]) for site in config["sender_candidates"] + config["receiver_candidates"]} | {0, 5, 9, 14, 18, 23})
    sites = adapter.identify_components(layers)
    by_id = {site.component_id: site for site in sites}
    clean_sender_inputs = adapter.tokenize([_sender_prompt(adapter, _input(case, "A")) for case in cases])
    attacked_sender_inputs = adapter.tokenize([_sender_prompt(adapter, _input(case, "B")) for case in cases])
    sender_positions = _aligned_positions(clean_sender_inputs["input_ids"], attacked_sender_inputs["input_ids"])
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
    clean_receiver_inputs = adapter.tokenize([_receiver_prompt(adapter, message.serialize()) for message in clean_messages])
    attacked_receiver_inputs = adapter.tokenize([_receiver_prompt(adapter, message.serialize()) for message in attacked_messages])
    receiver_positions = _aligned_positions(clean_receiver_inputs["input_ids"], attacked_receiver_inputs["input_ids"])
    clean_logits, clean_receiver_acts = _capture(adapter, clean_receiver_inputs, sites)
    attacked_logits, attacked_receiver_acts = _capture(adapter, attacked_receiver_inputs, sites)
    budget.receiver_forwards += 2
    clean_scores = escalation_margin(clean_logits, label_ids)
    attacked_scores = escalation_margin(attacked_logits, label_ids)

    sender_results = []
    for candidate in config["sender_candidates"]:
        site = by_id[candidate]
        rescue = _sender_patch(adapter, site, clean_sender_acts[candidate], attacked_sender_inputs, sender_positions["decision"], prompt_length, cases, label_ids, budget)
        induction = _sender_patch(adapter, site, attacked_sender_acts[candidate], clean_sender_inputs, sender_positions["decision"], prompt_length, cases, label_ids, budget)
        shuffled = _sender_patch(adapter, site, torch.roll(clean_sender_acts[candidate], 1, 0), attacked_sender_inputs, sender_positions["decision"], prompt_length, cases, label_ids, budget)
        rescue_values = _recovery(clean_scores, attacked_scores, rescue["scores"])
        induction_values = _induction(clean_scores, attacked_scores, induction["scores"])
        shuffled_values = _recovery(clean_scores, attacked_scores, shuffled["scores"])
        sender_results.append({"candidate_id": f"sender.{candidate}", "component_type": site.component_type, "rescue": _stats(rescue_values), "rescue_decision_fraction": sum(message.decision_code == "A" for message in rescue["messages"]) / len(cases), "induction": _stats(induction_values), "induction_decision_fraction": sum(message.decision_code == "B" for message in induction["messages"]) / len(cases), "shuffled_rescue": _stats(shuffled_values), "paired_message_hash_changed": sum(rescue["messages"][i].sha256() != attacked_messages[i].sha256() for i in range(len(cases))), "shuffled_mapping": {pair_ids[i]: pair_ids[(i - 1) % len(pair_ids)] for i in range(len(pair_ids))}, "runtime_seconds": rescue["runtime_seconds"] + induction["runtime_seconds"] + shuffled["runtime_seconds"]})

    receiver_results = []
    for candidate in config["receiver_candidates"]:
        site = by_id[candidate]
        rescue = _receiver_patch(adapter, site, clean_receiver_acts[candidate], attacked_receiver_inputs, receiver_positions["decision"], label_ids, budget)
        induction = _receiver_patch(adapter, site, attacked_receiver_acts[candidate], clean_receiver_inputs, receiver_positions["decision"], label_ids, budget)
        shuffled = _receiver_patch(adapter, site, torch.roll(clean_receiver_acts[candidate], 1, 0), attacked_receiver_inputs, receiver_positions["decision"], label_ids, budget)
        receiver_results.append({"candidate_id": f"receiver.{candidate}", "component_type": site.component_type, "rescue": _stats(_recovery(clean_scores, attacked_scores, rescue["scores"])), "induction": _stats(_induction(clean_scores, attacked_scores, induction["scores"])), "shuffled_rescue": _stats(_recovery(clean_scores, attacked_scores, shuffled["scores"])), "fixed_attacked_message_sha256": [message.sha256() for message in attacked_messages], "fixed_clean_message_sha256": [message.sha256() for message in clean_messages], "shuffled_mapping": {pair_ids[i]: pair_ids[(i - 1) % len(pair_ids)] for i in range(len(pair_ids))}, "runtime_seconds": rescue["runtime_seconds"] + induction["runtime_seconds"] + shuffled["runtime_seconds"]})

    position_results: dict[str, dict[str, object]] = {"sender": {}, "receiver": {}}
    sender_top = config["position_specificity_candidates"]["sender"]
    for name in ("evidence", "irrelevant"):
        run = _sender_patch(adapter, by_id[sender_top], clean_sender_acts[sender_top], attacked_sender_inputs, sender_positions[name], prompt_length, cases, label_ids, budget)
        position_results["sender"][name] = _stats(_recovery(clean_scores, attacked_scores, run["scores"]))
    receiver_top = config["position_specificity_candidates"]["receiver"]
    for name in ("evidence", "irrelevant"):
        run = _receiver_patch(adapter, by_id[receiver_top], clean_receiver_acts[receiver_top], attacked_receiver_inputs, receiver_positions[name], label_ids, budget)
        position_results["receiver"][name] = _stats(_recovery(clean_scores, attacked_scores, run["scores"]))

    controls = _sample_controls(config, sites)
    control_results = []
    for control in controls:
        site = by_id[control["site"]]
        if control["role"] == "sender":
            run = _sender_patch(adapter, site, clean_sender_acts[site.component_id], attacked_sender_inputs, sender_positions["decision"], prompt_length, cases, label_ids, budget)
        else:
            run = _receiver_patch(adapter, site, clean_receiver_acts[site.component_id], attacked_receiver_inputs, receiver_positions["decision"], label_ids, budget)
        control_results.append({**control, "candidate_id": f"{control['role']}.{control['site']}", "component_type": site.component_type, "rescue": _stats(_recovery(clean_scores, attacked_scores, run["scores"]))})

    zero_results = []
    for role, candidates, inputs, positions in (("sender", config["sender_candidates"], clean_sender_inputs, sender_positions), ("receiver", config["receiver_candidates"], clean_receiver_inputs, receiver_positions)):
        for candidate in candidates:
            site = by_id[candidate]
            try:
                adapter.install_zero_intervention_at_positions(site, [positions["decision"]])
                if role == "sender":
                    generated = adapter.generate(inputs, 1)
                    budget.sender_generations += 1
                    outputs = [adapter.tokenizer.decode(row[prompt_length:], skip_special_tokens=True) for row in generated]
                    messages = [MediatorMessage.from_sender_code(str(case["task_id"]), output, "authoritative ECG tool analysis") for case, output in zip(cases, outputs)]
                    scores, _, _ = _score_messages(adapter, messages, label_ids)
                    budget.receiver_forwards += 1
                else:
                    scores = escalation_margin(adapter.forward(inputs).logits, label_ids)
                    budget.receiver_forwards += 1
                applications = adapter.intervention_applications
            finally:
                adapter.remove_hooks()
            zero_results.append({"candidate_id": f"{role}.{candidate}", "operator": "clean_execution_zero_ablation_at_decision_position", "necessity_like_attack_fraction": _stats(_induction(clean_scores, attacked_scores, scores)), "applications": applications})

    assessments = [
        _evaluate_candidate(row, "sender", control_results, position_results, config)
        for row in sender_results
    ] + [
        _evaluate_candidate(row, "receiver", control_results, position_results, config)
        for row in receiver_results
    ]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results_path = OUTPUT_DIR / "hardening_results.json"
    results_payload = {"sender": sender_results, "receiver": receiver_results, "positions": position_results, "controls": control_results, "zero_ablation": zero_results, "assessments": assessments}
    results_path.write_text(json.dumps(results_payload, indent=2), encoding="utf-8")
    evidence = []
    for assessment in assessments:
        role = assessment["candidate_id"].split(".", 1)[0]
        row = next(item for item in (sender_results if role == "sender" else receiver_results) if item["candidate_id"] == assessment["candidate_id"])
        evidence.append(CausalEdgeEvidence(f"{assessment['candidate_id']}->{'message' if role == 'sender' else 'outcome'}", assessment["candidate_id"], "message.decision_code" if role == "sender" else "receiver.outcome", f"{role}_internal", "message_field" if role == "sender" else "outcome", "bidirectional_activation_intervention", "paired_replacement_with_specificity_controls", tuple(pair_ids), len(pair_ids), len(pair_ids), tuple(row["rescue"]["values"]), row["rescue"]["median"], "bidirectional_expected" if assessment["status"] == "supported" else "specificity_failed", assessment["matched_control_median"], (str(results_path),), (str(OUTPUT_DIR / "manifest.json"),), "development", assessment["status"]))
    evidence_path = OUTPUT_DIR / "revised_dcmg_evidence.json"
    evidence_path.write_text(json.dumps([edge.to_dict() for edge in evidence], indent=2), encoding="utf-8")
    supported = [item["candidate_id"] for item in assessments if item["status"] == "supported"]
    summary = {"result_state": "DEV", "scope": "development_only", "validation_test_accessed": False, "protocol_hash": sha256_file(PROTOCOL_PATH), "config_hash": sha256_file(CONFIG_PATH), "split_hash": split_hash(splits), "coarse_sites_reclassified_as": "development_causal_responders", "retained_prior_strong_random_control": "sender.L23.block_output", "supported_internal_causal_candidates": supported, "assessment_outcome": "specific_candidates_found" if supported else "coarse_intervention_specificity_insufficient", "head_refinement": "not_performed_no_valid_pre_projection_per_head_instrumentation", "message_only_recovery": 1.0, "identity_patch_interpretation": "intervention_non_interference_not_defense_utility", "query_counts": asdict(budget), "total_queries": budget.total, "runtime_seconds": time.perf_counter() - started, "primary_claim_candidate": config["primary_incremental_value_claim"], "utc_timestamp": datetime.now(timezone.utc).isoformat()}
    summary_path = OUTPUT_DIR / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    artifacts = {str(path): sha256_file(path) for path in (results_path, evidence_path, summary_path)}
    manifest = {
        "manifest_version": "1.0.0",
        "experiment_id": "P0_cross_20261014_specificity_hardening_0",
        "run_id": "P0_cross_20261014_specificity_hardening_0",
        "utc_timestamp": summary["utc_timestamp"],
        "result_state": "DEV",
        "git_commit": "34848c1",
        "uncommitted_diff": True,
        "dataset_manifest_hashes": {"frozen_split": split_hash(splits)},
        "model_id": model_meta["model_id"],
        "model_revision": model_meta["model_revision"],
        "tokenizer_revision": model_meta["tokenizer_revision"],
        "prompt_versions": {"paired_trace": "foundation_v1"},
        "random_seeds": config["matched_random_controls"]["seeds"],
        "hardware": "CPU; torch float32 eager attention",
        "python_env_hash": sha256_file(Path("requirements-lock.txt")),
        "command_line": ".venv\\Scripts\\python.exe -m causal.run_specificity_hardening",
        "config_file": str(CONFIG_PATH),
        "raw_output_path": str(results_path),
        "protocol": str(PROTOCOL_PATH),
        "protocol_hash": sha256_file(PROTOCOL_PATH),
        "config": str(CONFIG_PATH),
        "config_hash": sha256_file(CONFIG_PATH),
        "split": "development",
        "split_hash": split_hash(splits),
        "pair_ids": pair_ids,
        "query_counts": asdict(budget),
        "artifacts": artifacts,
    }
    (OUTPUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
