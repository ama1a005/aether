"""Static safety checks for the retained real-Qwen red-team notebook."""

import json

from scripts.build_kaggle_qwen_red_team_notebook import build


def test_notebook_is_pinned_gpu_resumable_and_hf_retained() -> None:
    commit = "a" * 40
    notebook = build(commit)
    source = "".join("".join(cell["source"]) for cell in notebook["cells"])
    assert commit in source
    assert "torch.cuda.is_available" in source and "cuda:0" not in source
    assert "HF_TOKEN" in source and "AETHER_HF_REPO" in source
    assert "checkpoint.tar.gz" in source and "final-results.tar.gz" in source
    assert "--resume" in source and "plan.json" in source
    assert "scripts.verify_external_bundle" in source
    for index, cell in enumerate(notebook["cells"]):
        if cell["cell_type"] == "code":
            compile("".join(cell["source"]), f"cell-{index}", "exec")
    json.dumps(notebook, allow_nan=False)
