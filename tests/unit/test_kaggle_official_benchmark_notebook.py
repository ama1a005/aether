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
    bfcl_source = "".join("".join(cell["source"]) for cell in build("bfcl", commit)["cells"])
    assert "vllm'" in bfcl_source and "--torch-backend'" in bfcl_source
    assert "verify_protocol_approval" in bfcl_source
    assert "AETHER_BFCL_ATTEMPT" in bfcl_source
    assert "requirements-bfcl-vllm.txt" in bfcl_source
    assert "vllm==0.34.0" not in bfcl_source  # version is centralized in the overlay file
    assert "uv==0.11.8" in bfcl_source
    assert "Refusing to repeat or overwrite this attempt" in bfcl_source
    assert "git','fetch','origin','m1/target-harness'" in bfcl_source
    assert "Retaining a blocked/failed BFCL attempt; this is not a score." in bfcl_source
    assert "verify_bfcl_bundle" in bfcl_source
    assert "aether-bfcl-official-{ATTEMPT}-results.tar.gz" in bfcl_source
    assert bfcl_source.index("tarfile.open") < bfcl_source.index("verify_bfcl_bundle")
    assert "--no-deps','-e'" not in bfcl_source


def test_official_notebook_rejects_mutable_source_identity() -> None:
    with pytest.raises(ValueError, match="immutable"):
        build("bfcl", "main")
