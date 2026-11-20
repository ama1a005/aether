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
    assert "if not PY.is_file()" in source and "if not REPO.exists()" in source
    assert "'-m','ensurepip','--upgrade'" in source
    assert "RepositoryNotFoundError" in source and "private=True" in source
    assert "'tokenizer_revision':REVISION" in source
    assert "upload_file_retry" in source and "range(1,5)" in source
    assert "scripts.verify_qwen_red_team_bundle" in source
    assert "AETHER_RED_TEAM_ATTEMPT" in source and "attempt-2" in source
    for index, cell in enumerate(notebook["cells"]):
        if cell["cell_type"] == "code":
            compile("".join(cell["source"]), f"cell-{index}", "exec")
    json.dumps(notebook, allow_nan=False)
