"""Run the bounded GPT-2 Small IOI causal calibration."""

from __future__ import annotations

import csv
import json
import random
import time
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
import numpy as np
import torch

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from calibration.ioi.dataset import build_fixed_ioi_dataset, validate_with_tokenizer, write_dataset
from calibration.ioi.gpt2_adapter import GPT2IOIAdapter, Head
from calibration.ioi.metrics import logit_difference, normalized_recovery
from experiments.manifest import create_run_manifest, write_run_manifest

EXPERIMENT_ID = "P0_mech_20261013_gpt2_ioi_calibration_0"
RUN_ID = "gpt2_ioi_calibration_0"


def _mean_ci(values: torch.Tensor) -> tuple[float, float, float]:
    array = values.detach().cpu().numpy()
    mean = float(array.mean())
    if len(array) < 2:
        return mean, mean, mean
    se = float(array.std(ddof=1) / np.sqrt(len(array)))
    return mean, mean - 1.96 * se, mean + 1.96 * se


def _run_patch(
    adapter: GPT2IOIAdapter,
    corrupted_inputs: dict[str, torch.Tensor],
    heads: list[Head],
    clean_cache: dict[str, torch.Tensor],
) -> torch.Tensor:
    try:
        adapter.install_head_patch_hooks(heads, clean_cache)
        return adapter.forward(corrupted_inputs).logits
    finally:
        adapter.remove_hooks()


def main() -> None:
    """Execute baseline, passive capture, known patches, and matched controls."""
    torch.manual_seed(0)
    registry_path = Path("configs/models/gpt2_calibration_registry.json")
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    reference = json.loads(Path("calibration/ioi/reference_circuit.json").read_text(encoding="utf-8"))
    acceptance = json.loads(Path("calibration/ioi/acceptance.json").read_text(encoding="utf-8"))
    adapter = GPT2IOIAdapter(Path(registry["local_path"]), registry["model_revision"])
    started = time.perf_counter()
    adapter.load()

    examples = build_fixed_ioi_dataset()
    validate_with_tokenizer(examples, adapter.tokenizer)
    dataset_path = Path("calibration/ioi/fixed_prompts.json")
    dataset_hash = write_dataset(examples, dataset_path, registry["tokenizer_revision"])
    clean_inputs = adapter.tokenize([example.clean_prompt for example in examples])
    corrupted_inputs = adapter.tokenize([example.corrupted_prompt for example in examples])
    if clean_inputs["input_ids"].shape != corrupted_inputs["input_ids"].shape:
        raise AssertionError("clean/corrupted batches must have identical shapes")
    io_ids = torch.tensor(
        [adapter.tokenizer.encode(" " + e.io_name, add_special_tokens=False)[0] for e in examples]
    )
    subject_ids = torch.tensor(
        [adapter.tokenizer.encode(" " + e.subject_name, add_special_tokens=False)[0] for e in examples]
    )

    clean_logits = adapter.forward(clean_inputs).logits
    corrupted_logits = adapter.forward(corrupted_inputs).logits
    clean_diff = logit_difference(clean_logits, io_ids, subject_ids)
    corrupted_diff = logit_difference(corrupted_logits, io_ids, subject_ids)
    clean_accuracy = float((clean_diff > 0).float().mean())
    if clean_accuracy < acceptance["baseline_accuracy_minimum"]:
        raise AssertionError(f"baseline IOI accuracy {clean_accuracy:.3f} failed predeclared gate")

    all_sites = adapter.identify_components(list(range(adapter.model.config.n_layer)))
    try:
        adapter.install_capture_hooks(all_sites)
        observed_logits = adapter.forward(clean_inputs).logits
    finally:
        adapter.remove_hooks()
    max_passive_delta = float((clean_logits - observed_logits).abs().max())
    if not torch.allclose(
        clean_logits,
        observed_logits,
        rtol=acceptance["passive_fp32_rtol"],
        atol=acceptance["passive_fp32_atol"],
    ):
        raise AssertionError(f"passive capture altered logits by {max_passive_delta}")
    if not torch.equal(clean_logits.argmax(-1), observed_logits.argmax(-1)):
        raise AssertionError("passive capture altered argmax predictions")
    clean_cache = dict(adapter.activations)

    known_heads = [tuple(head) for head in reference["tested_known_subset"]]
    known_logits = _run_patch(adapter, corrupted_inputs, known_heads, clean_cache)
    known_diff = logit_difference(known_logits, io_ids, subject_ids)
    individual_results = []
    for head in known_heads:
        patched = logit_difference(
            _run_patch(adapter, corrupted_inputs, [head], clean_cache), io_ids, subject_ids
        )
        individual_results.append(
            {
                "kind": "known_individual",
                "identity": [list(head)],
                "seed": None,
                "mean_logit_difference": float(patched.mean()),
                "normalized_recovery": normalized_recovery(
                    float(clean_diff.mean()), float(corrupted_diff.mean()), float(patched.mean())
                ),
            }
        )

    published = {tuple(head) for heads in reference["components"].values() for head in heads}
    candidates = [
        (layer, head)
        for layer in range(adapter.model.config.n_layer)
        for head in range(adapter.model.config.n_head)
        if (layer, head) not in published
    ]
    control_results = []
    for seed in acceptance["random_control_seeds"]:
        sampled = random.Random(seed).sample(candidates, len(known_heads))
        patched = logit_difference(
            _run_patch(adapter, corrupted_inputs, sampled, clean_cache), io_ids, subject_ids
        )
        control_results.append(
            {
                "kind": "matched_random",
                "identity": [list(head) for head in sampled],
                "seed": seed,
                "mean_logit_difference": float(patched.mean()),
                "normalized_recovery": normalized_recovery(
                    float(clean_diff.mean()), float(corrupted_diff.mean()), float(patched.mean())
                ),
            }
        )

    known_recovery = normalized_recovery(
        float(clean_diff.mean()), float(corrupted_diff.mean()), float(known_diff.mean())
    )
    control_mean = float(np.mean([row["normalized_recovery"] for row in control_results]))
    known_minus_control = known_recovery - control_mean
    acceptance_passed = (
        known_recovery > control_mean
        and known_minus_control >= acceptance["known_minus_control_minimum"]
    )
    clean_summary = _mean_ci(clean_diff)
    corrupted_summary = _mean_ci(corrupted_diff)
    result = {
        "experiment_id": EXPERIMENT_ID,
        "run_id": RUN_ID,
        "utc_timestamp": datetime.now(timezone.utc).isoformat(),
        "model": registry,
        "dataset": {"count": len(examples), "sha256": dataset_hash, "token_shape": list(clean_inputs["input_ids"].shape)},
        "baseline": {
            "accuracy": clean_accuracy,
            "mean_logit_difference": clean_summary[0],
            "mean_95ci": [clean_summary[1], clean_summary[2]],
            "median_logit_difference": float(clean_diff.median()),
            "error_pair_ids": [e.pair_id for e, value in zip(examples, clean_diff) if value <= 0],
            "corrupted_mean_logit_difference": corrupted_summary[0],
            "corrupted_mean_95ci": [corrupted_summary[1], corrupted_summary[2]],
        },
        "passive_non_interference": {
            "max_absolute_logit_difference": max_passive_delta,
            "argmax_identical": True,
            "hooks_remaining": len(adapter._handles),
        },
        "known_group": {
            "identity": [list(head) for head in known_heads],
            "mean_logit_difference": float(known_diff.mean()),
            "normalized_recovery": known_recovery,
        },
        "known_individual": individual_results,
        "matched_random_controls": control_results,
        "comparison": {
            "control_mean_normalized_recovery": control_mean,
            "known_minus_control": known_minus_control,
            "acceptance_passed": acceptance_passed,
            "criterion": acceptance,
        },
        "timing_seconds": {"total": time.perf_counter() - started},
    }
    if not acceptance_passed:
        raise AssertionError(f"known-vs-control gate failed: {known_minus_control:.4f}")

    output_dir = Path("results/calibration/ioi")
    output_dir.mkdir(parents=True, exist_ok=True)
    result_path = output_dir / "summary.json"
    result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    csv_path = output_dir / "patching_results.csv"
    rows = [
        {
            "kind": "known_group",
            "identity": json.dumps(result["known_group"]["identity"]),
            "seed": "",
            "mean_logit_difference": result["known_group"]["mean_logit_difference"],
            "normalized_recovery": known_recovery,
        },
        *individual_results,
        *control_results,
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    figure_path = output_dir / "known_vs_random.png"
    plt.figure(figsize=(6, 4))
    plt.bar(["known group", "random mean"], [known_recovery, control_mean])
    plt.ylabel("Normalized IOI recovery")
    plt.tight_layout()
    plt.savefig(figure_path, dpi=160)
    plt.close()

    manifest = create_run_manifest(
        experiment_id=EXPERIMENT_ID,
        run_id=RUN_ID,
        model_id=registry["model_id"],
        model_revision=registry["model_revision"],
        tokenizer_revision=registry["tokenizer_revision"],
        dataset_id="fixed_ioi_calibration",
        dataset_version="1.0.0",
        dataset_split="calibration",
        subset_ids=[example.pair_id for example in examples],
        seeds=[0, *acceptance["random_control_seeds"]],
        config_file=Path("calibration/ioi/acceptance.json"),
        raw_output_path=result_path,
        prompt_files=[dataset_path],
        intervention_config={"operator": "paired_clean_head_output_patch", "position": "end"},
        artifact_paths=[dataset_path, result_path, csv_path, figure_path],
        timing_seconds=result["timing_seconds"],
    )
    manifest_path = output_dir / "manifest.json"
    write_run_manifest(manifest, manifest_path)
    print(json.dumps(result, indent=2))
    print(f"manifest: {manifest_path}")


if __name__ == "__main__":
    main()
