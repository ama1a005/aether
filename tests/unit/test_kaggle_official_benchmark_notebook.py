"""Compilation and provenance tests for official benchmark notebooks."""

import pytest
import re

from scripts.build_kaggle_official_benchmark_notebook import UV_VERSION_PARSER, build


def test_uv_version_parser_handles_platform_suffix_and_rejects_bad_output() -> None:
    namespace = {"re": re}
    exec(UV_VERSION_PARSER, namespace)
    parse = namespace["parse_uv_version"]
    assert parse("uv 0.11.8 (x86_64-unknown-linux-gnu)") == "0.11.8"
    assert parse("uv 0.11.8") == "0.11.8"
    with pytest.raises(RuntimeError, match="Could not parse uv version"):
        parse("uv (x86_64-unknown-linux-gnu)")


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
    assert "'-m','ensurepip','--upgrade'" in bfcl_source
    assert "'-m','pip','--version'" in bfcl_source
    assert "if not PY.is_file()" in bfcl_source and "if not REPO.exists()" in bfcl_source
    assert "requirements-without-torch.txt" in bfcl_source
    assert "if not line.startswith('torch==')" in bfcl_source
    assert "installed['torch'].split('+',1)[0]=='2.14.0'" in bfcl_source
    assert "installed['cuda']=='13.0'" in bfcl_source
    assert "installed['cuda_available'] is True" in bfcl_source
    assert "startswith('0.34.0 2.14.0+ 13.0')" not in bfcl_source
    assert "Refusing to repeat or overwrite this attempt" in bfcl_source
    assert "git','fetch','origin','m1/target-harness'" in bfcl_source
    assert "Retaining a blocked/failed BFCL attempt; this is not a score." in bfcl_source
    assert "verify_bfcl_bundle" in bfcl_source
    assert "parse_uv_version" in bfcl_source
    assert "SETUP_COMPLETE=True" in bfcl_source
    assert "DEPENDENCIES_COMPLETE=True" in bfcl_source
    assert "sys.path.insert(0,str(REPO))" in bfcl_source
    assert "PREFLIGHT_COMPLETE=True" in bfcl_source
    assert "Dependency installation or model-free tests did not complete" in bfcl_source
    assert "Expected pinned repository commit" in bfcl_source
    assert "aether-bfcl-official-{ATTEMPT}-results.tar.gz" in bfcl_source
    assert bfcl_source.index("verify_bfcl_bundle") < bfcl_source.rindex("tarfile.open")
    assert "AETHER_HF_REPO" in bfcl_source and "HF_TOKEN" in bfcl_source
    assert "RepositoryNotFoundError" in bfcl_source and "private=True" in bfcl_source
    assert "checkpoint.tar.gz" in bfcl_source and "final-results.tar.gz" in bfcl_source
    assert "sync_stop.wait(300)" in bfcl_source
    assert "upload_file_retry" in bfcl_source and "range(1,5)" in bfcl_source
    assert "sync_thread.join()" in bfcl_source
    assert "sync_thread.join(timeout=15)" not in bfcl_source
    assert "--no-deps','-e'" not in bfcl_source


def test_official_notebook_rejects_mutable_source_identity() -> None:
    with pytest.raises(ValueError, match="immutable"):
        build("bfcl", "main")
