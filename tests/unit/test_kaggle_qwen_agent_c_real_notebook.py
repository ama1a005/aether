"""Static safety checks for the real-Qwen Agent C Kaggle notebook."""

from scripts.build_kaggle_qwen_agent_c_real_notebook import build


def test_notebook_is_pinned_gpu_enabled_and_checkpoint_safe() -> None:
    commit = "a" * 40; notebook = build(commit)
    source = "".join("".join(cell["source"]) for cell in notebook["cells"])
    assert commit in source
    assert "torch.cuda.is_available" in source and "float16" not in source
    assert "HF_TOKEN" in source and "AETHER_HF_REPO" in source
    assert "checkpoint_state.json" in source and "--resume" in source
    assert "scripts.verify_qwen_agent_c_real_bundle" in source
    assert "validation" not in source.lower() and "test split" not in source.lower()
