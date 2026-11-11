"""Model-independent tests for the frozen real-Qwen audit runner."""

from __future__ import annotations

import json
from types import SimpleNamespace

from instrumentation import run_qwen_causal_audit as runner


def test_audit_preflight_records_locked_splits(monkeypatch, tmp_path) -> None:
    base = {"model_id": "model", "model_revision": "revision"}
    protocol = {"protocol_version": "QCI-A1.0"}
    rows = [{"case_id": "a"}, {"case_id": "b"}]
    candidates = [SimpleNamespace(agent="sender", candidate_id="module.L1.mlp_output")]
    plan = {"candidate_ids": ["sender.module.L1.mlp_output"]}
    monkeypatch.setattr(runner, "_load_audit_inputs", lambda _root: (base, protocol, rows, candidates, plan))
    monkeypatch.setattr(runner, "measure_hardware", lambda _cache: {"decision": {"overall": "PASS"}})
    monkeypatch.setattr(runner, "_environment_inventory", lambda: ([], "environment"))
    monkeypatch.setattr(runner, "_git", lambda *_args: "commit" if _args[0] == "rev-parse" else "")
    monkeypatch.setattr(runner, "sha256_file", lambda _path: "hash")
    output = tmp_path / "output"
    result = runner.preflight(output, tmp_path / "cache", tmp_path / "discovery")
    assert result["decision"]["overall"] == "PASS"
    assert result["development_audit_executions"] == 0
    assert result["validation_executions"] == result["test_executions"] == 0
    assert json.loads((output / "audit_preflight.json").read_text())["audit_plan"] == plan


def test_failed_audit_execution_count_uses_retained_rows(tmp_path) -> None:
    (tmp_path / "raw_audit_interventions.jsonl").write_text("{}\n{}\n", encoding="utf-8")
    (tmp_path / "message_positive_controls.json").write_text("[{}, {}]", encoding="utf-8")
    assert runner._completed_audit_executions(tmp_path) == 4
