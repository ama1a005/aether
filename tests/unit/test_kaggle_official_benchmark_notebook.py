"""Compilation and provenance tests for official benchmark notebooks."""

import pytest

from scripts.build_kaggle_official_benchmark_notebook import build


def test_official_notebooks_are_commit_pinned_and_verified() -> None:
    commit = "a" * 40
    for benchmark in ("bfcl", "agentdojo"):
        notebook = build(benchmark, commit)
        source = "".join("".join(cell["source"]) for cell in notebook["cells"])
        assert commit in source and "scripts.verify_external_bundle" in source
        assert f"{benchmark}_official" in source
        for index, cell in enumerate(notebook["cells"]):
            if cell["cell_type"] == "code":
                assert cell["outputs"] == []
                compile("".join(cell["source"]), f"cell-{index}", "exec")
    assert "model_snapshot_manifest.json" in "".join(
        "".join(cell["source"]) for cell in build("bfcl", commit)["cells"])


def test_official_notebook_rejects_mutable_source_identity() -> None:
    with pytest.raises(ValueError, match="immutable"):
        build("bfcl", "main")
