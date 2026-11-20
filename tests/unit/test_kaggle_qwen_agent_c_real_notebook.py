"""Static safety checks for the real-Qwen Agent C Kaggle notebook."""

import json

from scripts.build_kaggle_qwen_agent_c_real_notebook import build


def test_notebook_is_pinned_gpu_enabled_and_checkpoint_safe() -> None:
    commit = "a" * 40; notebook = build(commit)
    source = "".join("".join(cell["source"]) for cell in notebook["cells"])
    assert commit in source
    assert "torch.cuda.is_available" in source and "float16" not in source
    assert "HF_TOKEN" in source and "AETHER_HF_REPO" in source
    assert "checkpoint_state.json" in source and "--resume" in source
    assert "if not PY.is_file()" in source and "if not REPO.exists()" in source
    assert "'-m','ensurepip','--upgrade'" in source
    assert "RepositoryNotFoundError" in source and "private=True" in source
    assert "mcp==1.27.1" in source
    assert "test_qwen_agent_c_real_mcp.py" in source
    assert "'tokenizer_revision':REVISION" in source
    assert "scripts.verify_qwen_agent_c_real_bundle" in source
    assert "validation" not in source.lower() and "test split" not in source.lower()
    assert "final-results.tar.gz" in source
    for index, cell in enumerate(notebook["cells"]):
        if cell["cell_type"] == "code":
            compile("".join(cell["source"]), f"cell-{index}", "exec")
    json.dumps(notebook, allow_nan=False)
