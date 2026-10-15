"""Run balanced-V2 behavior and message-level causal controls on development only."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time

import torch

from experiments.manifest import sha256_file
from instrumentation.adapters import Qwen2ModelAdapter
from paired_trace.balanced_v2 import case_normalized_margin, require_v2_development
from paired_trace.metrics import mediation_recovery, validate_label_tokens
from paired_trace.run_foundation import _input, _receiver_prompt, _sender_prompt
from paired_trace.schemas import MediatorMessage

CONFIG_PATH = Path("configs/experiments/balanced_v2_redesign_v2_1.json")
OUTPUT_ROOT = Path("results/phase1/balanced_v2")


def _select_cases(registry: dict[str, object], mode: str, split: str) -> list[dict[str, object]]:
    if split != "development":
        raise PermissionError(f"V2 {split} execution is locked before method freeze")
    development = [case for case in registry["cases"] if case["split"] == split]
    for case in development:
        require_v2_development(case)
    if mode == "smoke":
        return [case for label in ("A", "B") for case in development if case["ground_truth_code"] == label][:4] + [
            case for case in development if case["ground_truth_code"] == "B"
        ][:4]
    return development


def _generated_codes(adapter: Qwen2ModelAdapter, generated: torch.Tensor, prompt_length: int) -> tuple[list[str], list[list[int]]]:
    codes = [adapter.tokenizer.decode([int(row[prompt_length])], skip_special_tokens=True).strip() for row in generated]
    token_ids = [[int(value) for value in row[prompt_length:].tolist()] for row in generated]
    return codes, token_ids


def _score_messages(
    adapter: Qwen2ModelAdapter,
    messages: list[MediatorMessage],
    label_ids: dict[str, int],
    correct_codes: list[str],
) -> dict[str, object]:
    inputs = adapter.tokenize([_receiver_prompt(adapter, message.serialize()) for message in messages])
    logits = adapter.forward(inputs).logits
    scores, raw_a, raw_b = case_normalized_margin(logits, label_ids, correct_codes)
    predicted = ["A" if float(a) >= float(b) else "B" for a, b in zip(raw_a, raw_b)]
    return {
        "scores": scores,
        "raw_a": raw_a,
        "raw_b": raw_b,
        "predicted": predicted,
        "inputs": inputs,
    }


def _direction_summary(cases: list[dict[str, object]], rows: list[dict[str, object]], direction: str) -> dict[str, object]:
    selected = [row for case, row in zip(cases, rows) if case["attack_direction"] == direction]
    return {
        "N_total": len(selected),
        "N_clean_correct": sum(row["clean_correct"] for row in selected),
        "N_attack_success": sum(row["attack_success"] for row in selected),
        "N_clean_incorrect": sum(not row["clean_correct"] for row in selected),
        "N_no_effect": sum(row["clean_code"] == row["attacked_code"] for row in selected),
        "N_invalid": sum(not row["clean_message_valid"] or not row["attacked_message_valid"] for row in selected),
    }


def main() -> None:
    """Execute V2 smoke or full development baseline; locked splits fail closed."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("smoke", "full"), default="full")
    parser.add_argument("--split", choices=("development", "validation", "test"), default="development")
    args = parser.parse_args()
    started = time.perf_counter()
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    registry_path = Path(config["dataset_registry"])
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    cases = _select_cases(registry, args.mode, args.split)
    model_meta = json.loads(Path(config["model_registry"]).read_text(encoding="utf-8"))
    adapter = Qwen2ModelAdapter(
        model_meta["local_path"], model_meta["model_revision"], Path(model_meta["cache_dir"]),
        torch.float32, "cpu", True,
    )
    adapter.load()
    adapter.tokenizer.padding_side = config["decoder_padding_side"]
    label_ids = validate_label_tokens(adapter.tokenizer)
    correct_codes = [str(case["ground_truth_code"]) for case in cases]
    clean_data = [_input(case, str(case["ground_truth_code"])) for case in cases]
    attacked_data = [_input(case, str(case["adversarial_code"])) for case in cases]
    clean_inputs = adapter.tokenize([_sender_prompt(adapter, item) for item in clean_data])
    attacked_inputs = adapter.tokenize([_sender_prompt(adapter, item) for item in attacked_data])
    if clean_inputs["input_ids"].shape != attacked_inputs["input_ids"].shape:
        raise ValueError("V2 sender pairs are not structurally aligned")
    prompt_length = clean_inputs["input_ids"].shape[1]
    clean_generated = adapter.generate_uncached(clean_inputs, config["sender_generation"]["max_new_tokens"])
    attacked_generated = adapter.generate_uncached(attacked_inputs, config["sender_generation"]["max_new_tokens"])
    clean_codes, clean_generated_ids = _generated_codes(adapter, clean_generated, prompt_length)
    attacked_codes, attacked_generated_ids = _generated_codes(adapter, attacked_generated, prompt_length)
    clean_messages = [
        MediatorMessage.from_sender_code(str(case["task_id"]), code, config["mediator_evidence"])
        for case, code in zip(cases, clean_codes)
    ]
    attacked_messages = [
        MediatorMessage.from_sender_code(str(case["task_id"]), code, config["mediator_evidence"])
        for case, code in zip(cases, attacked_codes)
    ]
    clean = _score_messages(adapter, clean_messages, label_ids, correct_codes)
    attacked = _score_messages(adapter, attacked_messages, label_ids, correct_codes)
    field_messages = [
        MediatorMessage.from_sender_code(str(case["task_id"]), str(case["ground_truth_code"]), config["mediator_evidence"])
        for case in cases
    ]
    field = _score_messages(adapter, field_messages, label_ids, correct_codes)
    rows = []
    for index, case in enumerate(cases):
        rows.append({
            "case_id": case["case_id"], "split": case["split"],
            "ground_truth_code": correct_codes[index], "adversarial_code": case["adversarial_code"],
            "attack_direction": case["attack_direction"], "template_family": case["template_family"],
            "clean_sender_code": clean_codes[index], "attacked_sender_code": attacked_codes[index],
            "clean_message_valid": clean_messages[index].valid, "attacked_message_valid": attacked_messages[index].valid,
            "clean_code": clean["predicted"][index], "attacked_code": attacked["predicted"][index],
            "clean_correct": clean["predicted"][index] == correct_codes[index],
            "attack_success": attacked["predicted"][index] == case["adversarial_code"],
            "clean_score": float(clean["scores"][index]), "attacked_score": float(attacked["scores"][index]),
            "clean_raw_logit_a": float(clean["raw_a"][index]), "clean_raw_logit_b": float(clean["raw_b"][index]),
            "attacked_raw_logit_a": float(attacked["raw_a"][index]), "attacked_raw_logit_b": float(attacked["raw_b"][index]),
            "prompt_token_ids": [int(value) for value in clean_inputs["input_ids"][index].tolist()],
            "clean_generated_token_ids": clean_generated_ids[index],
            "attacked_generated_token_ids": attacked_generated_ids[index],
            "decision_token_index": prompt_length,
            "decision_generation_step": 0,
            "prefix_tokens_before_decision": [int(value) for value in clean_inputs["input_ids"][index].tolist()],
            "post_decision_tokens": clean_generated_ids[index][1:],
            "clean_message_sha256": clean_messages[index].sha256(),
            "attacked_message_sha256": attacked_messages[index].sha256(),
        })
    eligible = [index for index, row in enumerate(rows) if row["clean_correct"] and row["attack_success"] and row["clean_message_valid"] and row["attacked_message_valid"]]
    message_metrics: dict[str, dict[str, object]] = {}
    for direction in ("A_TO_B", "B_TO_A"):
        indices = [i for i in eligible if cases[i]["attack_direction"] == direction]
        message_metrics[direction] = {
            "N_eligible": len(indices),
            "clean_message_rescue": [mediation_recovery(float(clean["scores"][i]), float(attacked["scores"][i]), float(clean["scores"][i])) for i in indices],
            "attacked_message_induction": [mediation_recovery(float(attacked["scores"][i]), float(clean["scores"][i]), float(attacked["scores"][i])) for i in indices],
            "decision_field_recovery": [mediation_recovery(float(clean["scores"][i]), float(attacked["scores"][i]), float(field["scores"][i])) for i in indices],
        }
    output_dir = OUTPUT_ROOT / f"{args.mode}_v2_1"
    output_dir.mkdir(parents=True, exist_ok=True)
    rows_path = output_dir / "development_rows.json"
    rows_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    summary = {
        "result_state": "DEV", "mode": args.mode, "executed_split": "development",
        "validation_test_accessed": False,
        "counts_by_direction": {direction: _direction_summary(cases, rows, direction) for direction in ("A_TO_B", "B_TO_A")},
        "message_controls_by_direction": message_metrics,
        "score_definition": "logit(correct_label)-logit(adversarial_label)",
        "sender_generation": {"decision_generation_step": 0, "use_cache": False, "max_new_tokens": 2},
        "query_counts": {"sender_generations": 2, "receiver_forwards": 3, "total": 5},
        "runtime_seconds": time.perf_counter() - started,
        "utc_timestamp": datetime.now(timezone.utc).isoformat(),
    }
    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    manifest = {
        "manifest_version": "1.0.0", "run_id": f"P0_cross_20261015_balanced_v2_{args.mode}_0",
        "utc_timestamp": summary["utc_timestamp"], "git_commit": "303e0d8", "uncommitted_diff": True,
        "dataset_manifest_hashes": {str(registry_path): sha256_file(registry_path), config["control_mappings"]: sha256_file(Path(config["control_mappings"]))},
        "model_id": model_meta["model_id"], "model_revision": model_meta["model_revision"],
        "tokenizer_revision": model_meta["tokenizer_revision"], "prompt_versions": {"sender": "balanced_v2_copy_code_v1", "receiver": "mediator_v1"},
        "random_seeds": [config["seed"]], "hardware": "CPU; torch float32 eager attention",
        "python_env_hash": sha256_file(Path("requirements-lock.txt")),
        "command_line": f"python -m paired_trace.run_balanced_v2_baseline --mode {args.mode} --split development",
        "config_file": str(CONFIG_PATH), "raw_output_path": str(rows_path),
        "subset_ids": [case["case_id"] for case in cases], "query_counts": summary["query_counts"],
        "artifacts": {str(rows_path): sha256_file(rows_path), str(summary_path): sha256_file(summary_path)},
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
