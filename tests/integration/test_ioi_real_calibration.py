"""Opt-in integration checks for the pinned GPT-2 IOI adapter."""

import json
import os
from pathlib import Path

import pytest
import torch

from calibration.ioi.dataset import build_fixed_ioi_dataset, validate_with_tokenizer
from calibration.ioi.gpt2_adapter import GPT2IOIAdapter


@pytest.mark.skipif(
    os.environ.get("AETHER_RUN_CALIBRATION_MODELS") != "1",
    reason="set AETHER_RUN_CALIBRATION_MODELS=1 when the pinned GPT-2 model is present",
)
def test_gpt2_prompt_assumptions_and_passive_hook_cleanup() -> None:
    registry = json.loads(
        Path("configs/models/gpt2_calibration_registry.json").read_text(encoding="utf-8")
    )
    adapter = GPT2IOIAdapter(Path(registry["local_path"]), registry["model_revision"])
    adapter.load()
    examples = build_fixed_ioi_dataset()
    validate_with_tokenizer(examples, adapter.tokenizer)
    inputs = adapter.tokenize([example.clean_prompt for example in examples])
    baseline = adapter.forward(inputs).logits
    sites = [site for site in adapter.identify_components([9]) if site.component_id == "L9.H9.z"]
    try:
        adapter.install_capture_hooks(sites)
        observed = adapter.forward(inputs).logits
    finally:
        adapter.remove_hooks()
    assert torch.equal(baseline, observed)
    assert "L9.H9.z" in adapter.activations
    assert adapter._handles == []
