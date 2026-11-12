"""Tests for the generated QCI-2 Kaggle notebook."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.build_kaggle_qwen_qci2_notebook import OUTPUT, REPOSITORY_COMMIT, build


ROOT = Path(__file__).resolve().parents[2]


def test_qci2_notebook_is_pinned_clean_and_matches_builder() -> None:
    notebook = build()
    assert json.loads(OUTPUT.read_text(encoding="utf-8")) == notebook
    source = "".join("".join(cell["source"]) for cell in notebook["cells"])
    assert REPOSITORY_COMMIT == "f26a3f0c932c652cc86d628fe6ac18bc9b08391a"
    assert "run_qwen_causal_semantic_interventions" in source
    assert "scripts.verify_qci2_bundle" in source
    assert "aether-qwen-qci2-results.tar.gz" in source
    assert "aether-qwen-qci2-checkpoint.tar.gz" in source
    assert "'--resume'" in source
    assert "AETHER_RUN_REAL_MODEL_TESTS" in source
    assert all(cell.get("outputs", []) == [] for cell in notebook["cells"] if cell["cell_type"] == "code")


def test_qci2_notebook_does_not_open_locked_splits() -> None:
    source = "".join("".join(cell["source"]) for cell in build()["cells"])
    assert "run_qwen_causal_audit" not in source
    assert "development_audit_executions" not in source
    assert "validation" not in source.lower().replace("validation and test remain closed", "")


def test_qci2_notebook_code_cells_compile() -> None:
    for cell in build()["cells"]:
        if cell["cell_type"] == "code":
            compile("".join(cell["source"]), f"notebook-cell-{cell['id']}", "exec")
