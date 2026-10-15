"""Predeclared passive-hook acceptance test for the pinned real model."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
import torch

from instrumentation.adapters import Qwen2ModelAdapter


MODEL_REGISTRY = Path("configs/models/model_registry.json")
FIXED_PROMPTS = (
    "Return exactly one word: SAFE",
    "What is 2 + 2? Answer with only the number.",
)
TOLERANCE = {
    torch.float32: {"rtol": 1e-5, "atol": 1e-6},
    torch.float16: {"rtol": 1e-3, "atol": 1e-3},
    torch.bfloat16: {"rtol": 5e-3, "atol": 5e-3},
}


@pytest.mark.skipif(
    os.environ.get("AETHER_RUN_REAL_MODEL_TESTS") != "1",
    reason="set AETHER_RUN_REAL_MODEL_TESTS=1 after the pinned model is present",
)
def test_read_only_hooks_do_not_change_qwen_computation(tmp_path: Path) -> None:
    """Greedy tokens and argmaxes must match; logits must meet dtype policy."""
    registry = json.loads(MODEL_REGISTRY.read_text(encoding="utf-8"))
    adapter = Qwen2ModelAdapter(
        model_id=registry["local_path"],
        revision=registry["model_revision"],
        cache_dir=Path(registry["cache_dir"]),
        dtype=getattr(torch, registry["dtype"]),
        device=registry["device"],
        local_files_only=True,
    )
    adapter.load()
    inputs = adapter.tokenize(FIXED_PROMPTS)
    baseline = adapter.forward(inputs).logits
    baseline_tokens = adapter.generate(inputs, max_new_tokens=4)
    sites = adapter.identify_components([0, len(adapter.model.model.layers) // 2, len(adapter.model.model.layers) - 1])
    try:
        adapter.install_capture_hooks(sites)
        observed = adapter.forward(inputs).logits
        observed_tokens = adapter.generate(inputs, max_new_tokens=4)
    finally:
        adapter.remove_hooks()

    policy = TOLERANCE[adapter.dtype]
    assert torch.equal(baseline.argmax(dim=-1), observed.argmax(dim=-1))
    assert torch.equal(baseline_tokens, observed_tokens)
    assert torch.allclose(baseline, observed, **policy)
    assert len(adapter._handles) == 0
    assert set(adapter.activations) == {site.component_id for site in sites}


@pytest.mark.skipif(
    os.environ.get("AETHER_RUN_REAL_MODEL_TESTS") != "1",
    reason="set AETHER_RUN_REAL_MODEL_TESTS=1 after the pinned model is present",
)
def test_qwen_generation_step_and_pre_projection_head_semantics() -> None:
    """Uncached decoding and passive pre-o_proj capture must be exact and removable."""
    registry = json.loads(MODEL_REGISTRY.read_text(encoding="utf-8"))
    adapter = Qwen2ModelAdapter(
        registry["local_path"], registry["model_revision"], Path(registry["cache_dir"]),
        getattr(torch, registry["dtype"]), registry["device"], True,
    )
    adapter.load()
    inputs = adapter.tokenize([FIXED_PROMPTS[0]])
    standard = adapter.generate(inputs, max_new_tokens=2)
    uncached = adapter.generate_uncached(inputs, max_new_tokens=2)
    assert torch.equal(standard, uncached)
    baseline_logits = adapter.forward(inputs).logits
    baseline_tokens = adapter.generate_uncached(inputs, max_new_tokens=2)
    layer = len(adapter.model.model.layers) // 2
    adapter.install_head_capture(layer)
    observed_logits = adapter.forward(inputs).logits
    observed_tokens = adapter.generate_uncached(inputs, max_new_tokens=2)
    concat = adapter.head_activations[f"L{layer}.pre_o_proj_concat"]
    heads = adapter.head_activations[f"L{layer}.pre_o_proj_heads"]
    adapter.remove_hooks()
    assert torch.equal(heads.reshape_as(concat), concat)
    assert torch.allclose(baseline_logits, observed_logits, **TOLERANCE[adapter.dtype])
    assert torch.equal(baseline_tokens, observed_tokens)
    assert adapter._handles == []
