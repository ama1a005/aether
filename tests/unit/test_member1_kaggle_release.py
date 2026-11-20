"""Combined release gate for the three user-facing Member-1 Kaggle notebooks."""

from __future__ import annotations

import json

from scripts.build_kaggle_official_benchmark_notebook import build as build_official
from scripts.build_kaggle_qwen_agent_c_real_notebook import build as build_agent_c
from scripts.build_kaggle_qwen_red_team_notebook import build as build_red_team


def _source(notebook: dict[str, object]) -> str:
    cells = notebook["cells"]
    assert isinstance(cells, list)
    for index, cell in enumerate(cells):
        assert isinstance(cell, dict)
        if cell["cell_type"] == "code":
            compile("".join(cell["source"]), f"release-cell-{index}", "exec")
            assert cell["outputs"] == [] and cell["execution_count"] is None
    json.dumps(notebook, allow_nan=False)
    return "\n".join("".join(cell["source"]) for cell in cells)


def test_member1_notebooks_share_complete_release_guards() -> None:
    commit = "a" * 40
    agent = _source(build_agent_c(commit))
    red = _source(build_red_team(commit))
    bfcl = _source(build_official("bfcl", commit))

    for source in (agent, red, bfcl):
        assert commit in source
        assert "3.11.9" in source
        assert "ensurepip" in source
        assert "HF_TOKEN" in source and "AETHER_HF_REPO" in source
        assert "RepositoryNotFoundError" in source
        assert "private=True" in source
        assert "upload_file_retry" in source
        assert "final-results.tar.gz" in source

    for source in (agent, red):
        assert "torch==2.14.1" in source
        assert "https://download.pytorch.org/whl/cu130" in source
        assert "if not x.startswith('torch==')" in source
        assert "'tokenizer_revision':REVISION" in source
        assert "scripts.verify_" in source

    assert "mcp==1.27.1" in agent
    assert "test_qwen_agent_c_real_mcp.py" in agent
    assert "checkpoint_state.json" in agent and "--resume" in agent
    assert "checkpoint.tar.gz" in red and "--resume" in red

    assert "bfcl_eval==2026.3.23" in bfcl
    assert "requirements-without-torch.txt" in bfcl
    assert "installed['vllm']=='0.34.0'" in bfcl
    assert "installed['torch'].split('+',1)[0]=='2.14.0'" in bfcl
    assert "installed['cuda']=='13.0'" in bfcl
    assert "verify_bfcl_bundle" in bfcl
