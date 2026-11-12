"""Tests for the conditional QCI-2A1 Kaggle notebook."""

from __future__ import annotations

import json

from scripts.build_kaggle_qwen_qci2_audit_notebook import OUTPUT, REPOSITORY_COMMIT, build


def test_qci2_audit_notebook_is_pinned_and_compiles() -> None:
    notebook = build()
    assert json.loads(OUTPUT.read_text(encoding="utf-8")) == notebook
    source = "".join("".join(cell["source"]) for cell in notebook["cells"])
    assert REPOSITORY_COMMIT == "f26a3f0c932c652cc86d628fe6ac18bc9b08391a"
    assert "run_qwen_causal_semantic_audit" in source
    assert "verify_qci2_bundle" in source and "verify_qci2_audit_bundle" in source
    assert "aether-qwen-qci2-results.tar.gz" in source
    assert "validation" in source.lower() and "test remain locked" in source.lower()
    for cell in notebook["cells"]:
        if cell["cell_type"] == "code": compile("".join(cell["source"]), cell["id"], "exec")
