"""Model-independent tests for the QCI-2 semantic audit runner."""

from __future__ import annotations

import json
from types import SimpleNamespace

from instrumentation import run_qwen_causal_semantic_audit as runner


def test_qci2_audit_preflight_records_plan_and_split_locks(monkeypatch, tmp_path) -> None:
    base = {"model_id": "model", "model_revision": "revision"}
    rows = [{"case_id": "a"}, {"case_id": "b"}]
    candidates = [SimpleNamespace(agent="sender", candidate_id="module.L1.mlp_output")]
    plan = {"candidate_ids": ["sender.module.L1.mlp_output"]}
    monkeypatch.setattr(runner, "_load_inputs", lambda _root: (base, {}, rows, candidates, plan))
    monkeypatch.setattr(runner, "measure_hardware", lambda _cache: {"decision": {"overall": "PASS"}})
    monkeypatch.setattr(runner, "_environment_inventory", lambda: ([], "environment"))
    monkeypatch.setattr(runner.qci1, "_git", lambda *_args: "commit" if _args[0] == "rev-parse" else "")
    monkeypatch.setattr(runner, "sha256_file", lambda _path: "hash")
    result = runner.preflight(tmp_path / "out", tmp_path / "cache", tmp_path / "discovery")
    assert result["decision"]["overall"] == "PASS"
    assert result["audit_plan"] == plan
    assert result["development_audit_executions"] == 0
    assert result["validation_executions"] == result["test_executions"] == 0
    assert json.loads((tmp_path / "out/audit_preflight.json").read_text())["model_accessed"] is False
