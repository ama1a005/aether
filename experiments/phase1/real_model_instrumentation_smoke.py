"""One deterministic real-model capture and intervention smoke experiment."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import torch
import transformers
import psutil

from experiments.manifest import create_run_manifest, sha256_file, write_run_manifest
from instrumentation.adapters import Qwen2ModelAdapter
from instrumentation.cache.activation_cache import ActivationCache

EXPERIMENT_ID = "P0_mech_20261012_real_instrumentation_0"
RUN_ID = "real_instrumentation_0"
SEED = 42
PROMPT_MESSAGES = [
    {"role": "system", "content": "You are a deterministic research assistant."},
    {"role": "user", "content": "Return exactly one word: SAFE"},
]


def main() -> None:
    """Run baseline, passive capture, artifact reload, and one zero intervention."""
    torch.manual_seed(SEED)
    process = psutil.Process()
    rss_before_load = process.memory_info().rss
    registry_path = Path("configs/models/model_registry.json")
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    adapter = Qwen2ModelAdapter(
        model_id=registry["local_path"],
        revision=registry["model_revision"],
        cache_dir=Path(registry["cache_dir"]),
        dtype=getattr(torch, registry["dtype"]),
        device=registry["device"],
        local_files_only=True,
    )

    started = time.perf_counter()
    adapter.load()
    load_seconds = time.perf_counter() - started
    rss_after_load = process.memory_info().rss
    rendered_prompt = adapter.tokenizer.apply_chat_template(
        PROMPT_MESSAGES, tokenize=False, add_generation_prompt=True
    )
    inputs = adapter.tokenize([rendered_prompt])

    inference_started = time.perf_counter()
    baseline_logits = adapter.forward(inputs).logits
    baseline_tokens = adapter.generate(inputs, max_new_tokens=4)
    baseline_seconds = time.perf_counter() - inference_started

    layer = len(adapter.model.model.layers) // 2
    site = next(
        candidate
        for candidate in adapter.identify_components([layer])
        if candidate.component_type == "mlp_output"
    )
    try:
        adapter.install_capture_hooks([site])
        observed_logits = adapter.forward(inputs).logits
        prompt_activation = adapter.activations[site.component_id].clone()
        observed_tokens = adapter.generate(inputs, max_new_tokens=4)
    finally:
        adapter.remove_hooks()

    tolerance = {"rtol": 1e-5, "atol": 1e-6}
    max_logit_difference = float((baseline_logits - observed_logits).abs().max())
    if not torch.equal(baseline_tokens, observed_tokens):
        raise AssertionError("passive hooks changed greedy output tokens")
    if not torch.allclose(baseline_logits, observed_logits, **tolerance):
        raise AssertionError(f"passive hook logit difference {max_logit_difference} exceeded policy")

    activation = prompt_activation
    cache = ActivationCache()
    artifact_path = cache.save(RUN_ID, site.component_id, activation)
    artifact_hash = sha256_file(artifact_path)
    reloaded = cache.load(RUN_ID, site.component_id)
    if not torch.equal(activation, reloaded):
        raise AssertionError("reloaded activation differs from captured activation")

    try:
        adapter.install_zero_intervention(site)
        intervened_logits = adapter.forward(inputs).logits
        intervened_tokens = adapter.generate(inputs, max_new_tokens=4)
    finally:
        adapter.remove_hooks()
    intervention_max_logit_difference = float(
        (baseline_logits - intervened_logits).abs().max()
    )
    if intervention_max_logit_difference == 0.0:
        raise AssertionError("zero intervention executed without measurable logit effect")
    final_memory = process.memory_info()
    prompt_length = inputs["input_ids"].shape[1]
    baseline_text = adapter.tokenizer.decode(
        baseline_tokens[0, prompt_length:], skip_special_tokens=True
    )
    observed_text = adapter.tokenizer.decode(
        observed_tokens[0, prompt_length:], skip_special_tokens=True
    )
    intervened_text = adapter.tokenizer.decode(
        intervened_tokens[0, prompt_length:], skip_special_tokens=True
    )

    result_path = Path("results/raw/real_model_instrumentation_smoke.json")
    result_path.parent.mkdir(parents=True, exist_ok=True)
    token_path = Path("results/raw/real_model_instrumentation_tokens.json")
    token_path.write_text(
        json.dumps(
            {
                "rendered_prompt": rendered_prompt,
                "input_token_ids": inputs["input_ids"].tolist(),
                "baseline_generated_ids": baseline_tokens.tolist(),
                "observed_generated_ids": observed_tokens.tolist(),
                "intervened_generated_ids": intervened_tokens.tolist(),
                "baseline_generated_text": baseline_text,
                "observed_generated_text": observed_text,
                "intervened_generated_text": intervened_text,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    result = {
        "experiment_id": EXPERIMENT_ID,
        "run_id": RUN_ID,
        "utc_timestamp": datetime.now(timezone.utc).isoformat(),
        "model_id": registry["model_id"],
        "model_revision": registry["model_revision"],
        "tokenizer_revision": registry["tokenizer_revision"],
        "dtype": registry["dtype"],
        "device": registry["device"],
        "attention_implementation": registry["attention_implementation"],
        "torch_version": torch.__version__,
        "transformers_version": transformers.__version__,
        "generation": {
            "do_sample": False,
            "max_new_tokens": 4,
            "seed": SEED,
            "baseline_text": baseline_text,
            "observed_text": observed_text,
            "intervened_text": intervened_text,
        },
        "capture": {
            "component_id": site.component_id,
            "component_type": site.component_type,
            "tensor_semantics": site.tensor_semantics,
            "token_positions": list(range(activation.shape[1])),
            "tensor_shape": list(activation.shape),
            "dtype": str(activation.dtype),
            "artifact_location": str(artifact_path),
            "artifact_hash": artifact_hash,
        },
        "non_interference": {
            "greedy_tokens_identical": True,
            "argmax_identical": bool(
                torch.equal(baseline_logits.argmax(-1), observed_logits.argmax(-1))
            ),
            "max_absolute_logit_difference": max_logit_difference,
            "tolerance": tolerance,
        },
        "intervention": {
            "operator": "zero_ablation",
            "component_id": site.component_id,
            "max_absolute_logit_difference": intervention_max_logit_difference,
            "generated_tokens_changed": not torch.equal(baseline_tokens, intervened_tokens),
            "hooks_remaining_after_run": len(adapter._handles),
        },
        "timing_seconds": {
            "model_load": load_seconds,
            "baseline_inference_and_generation": baseline_seconds,
            "total": time.perf_counter() - started,
        },
        "process_memory_bytes": {
            "rss_before_model_load": rss_before_load,
            "rss_after_model_load": rss_after_load,
            "rss_after_experiment": final_memory.rss,
            "peak_working_set": getattr(final_memory, "peak_wset", None),
        },
    }
    result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    manifest = create_run_manifest(
        experiment_id=EXPERIMENT_ID,
        run_id=RUN_ID,
        model_id=registry["model_id"],
        model_revision=registry["model_revision"],
        tokenizer_revision=registry["tokenizer_revision"],
        dataset_id="fixed_prompt_smoke",
        dataset_version="v1",
        dataset_split="not_applicable",
        subset_ids=["safe_prompt_0"],
        seeds=[SEED],
        config_file=registry_path,
        raw_output_path=result_path,
        prompt_files=[token_path],
        intervention_config={"operator": "zero_ablation", "component_id": site.component_id},
        artifact_paths=[artifact_path, token_path, result_path],
        timing_seconds=result["timing_seconds"],
    )
    manifest_path = Path("results/manifests") / f"{EXPERIMENT_ID}.json"
    write_run_manifest(manifest, manifest_path)
    print(json.dumps(result, indent=2))
    print(f"manifest: {manifest_path}")


if __name__ == "__main__":
    main()
