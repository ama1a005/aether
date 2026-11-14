"""Model-independent gates for the prospective CORE-02 seed sharding."""

from __future__ import annotations

import json
import ast
from pathlib import Path

import pytest

import instrumentation.run_qci2_matched_search as runner


def test_parallel_runner_rejects_missing_exact_approval(monkeypatch: pytest.MonkeyPatch,
                                                        tmp_path: Path) -> None:
    amendment = tmp_path / "amendment.yaml"
    amendment.write_text("frozen: true\n", encoding="utf-8")
    monkeypatch.setattr(runner, "V24", amendment)
    monkeypatch.setattr(runner, "V24_DECISION", tmp_path / "missing.json")
    with pytest.raises(PermissionError, match="awaits exact-hash approval"):
        runner._require_parallel_approval()


def test_parallel_runner_accepts_only_matching_approval(monkeypatch: pytest.MonkeyPatch,
                                                        tmp_path: Path) -> None:
    amendment = tmp_path / "amendment.yaml"
    amendment.write_text("frozen: true\n", encoding="utf-8")
    decision = tmp_path / "decision.json"
    decision.write_text(json.dumps({"decision": "APPROVED", "amendment_sha256": "wrong"}),
                        encoding="utf-8")
    monkeypatch.setattr(runner, "V24", amendment)
    monkeypatch.setattr(runner, "V24_DECISION", decision)
    with pytest.raises(PermissionError, match="does not approve"):
        runner._require_parallel_approval()
    decision.write_text(json.dumps({"decision": "APPROVED",
        "amendment_sha256": runner._hash(amendment)}), encoding="utf-8")
    assert runner._require_parallel_approval() == runner._hash(amendment)


def test_seed_selection_rejects_invalid_values(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unique subset"):
        runner.run(tmp_path / "out", tmp_path / "snapshot", resume=False, seeds=())
    with pytest.raises(ValueError, match="unique subset"):
        runner.run(tmp_path / "out", tmp_path / "snapshot", resume=False, seeds=(11, 11))
    with pytest.raises(ValueError, match="unique subset"):
        runner.run(tmp_path / "out", tmp_path / "snapshot", resume=False, seeds=(44,))


def test_generated_parallel_notebooks_are_seed_isolated_and_compile() -> None:
    root = Path(__file__).resolve().parents[2]
    expected_commit = "5a29be4826e90fa58affeac4faf015561cefc7dd"
    for seed in (11, 22, 33):
        path = root / f"notebooks/aether_qwen_core02_seed{seed}.ipynb"
        notebook = json.loads(path.read_text(encoding="utf-8"))
        source = "\n".join("".join(cell["source"]) for cell in notebook["cells"])
        assert f"SEED={seed}" in source
        assert expected_commit in source
        assert "scripts.verify_qci2_matched_search_shard" in source
        for cell in notebook["cells"]:
            if cell["cell_type"] == "code":
                ast.parse("".join(cell["source"]))
