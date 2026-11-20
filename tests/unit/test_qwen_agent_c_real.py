"""Model-independent acceptance tests for approved real-Qwen Agent C."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.phase1 import qwen_agent_c_real as agent_c_module
from experiments.external_bundle import artifact_hashes, write_bundle_manifest
from experiments.phase1.qwen_agent_c_real import (
    EXPECTED_HASH,
    evaluate_condition,
    load_protocol,
    parse_action,
    parse_review,
    summarize,
    verify_snapshot,
)
from scripts.ingest_qwen_agent_c_real_bundle import ingest
from scripts.verify_qwen_agent_c_real_bundle import verify


ROOT = Path(__file__).resolve().parents[2]


def test_required_upload_retries_then_succeeds(monkeypatch) -> None:
    class Hub:
        calls = 0

        def upload_file(self, **_arguments) -> None:
            self.calls += 1
            if self.calls < 3:
                raise OSError("temporary transport failure")

    hub = Hub()
    monkeypatch.setattr(agent_c_module.time, "sleep", lambda _seconds: None)
    agent_c_module._upload_with_retry(hub, path_or_fileobj="x")
    assert hub.calls == 3


def test_final_jsonl_export_replaces_interrupted_stale_file_atomically(tmp_path: Path) -> None:
    target = tmp_path / "raw_reviews.jsonl"
    target.write_text('{"stale":true}\n', encoding="utf-8")
    rows = [{"case_id": "case-1", "condition": "clean"},
            {"case_id": "case-1", "condition": "attacked"}]

    agent_c_module._atomic_jsonl(target, rows)

    assert [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines()] == rows
    assert not list(tmp_path.glob(".raw_reviews.jsonl.*"))


def test_approved_protocol_loads_without_model_access() -> None:
    protocol = load_protocol()
    assert protocol["model"]["model_id"] == "Qwen/Qwen2.5-1.5B-Instruct"
    assert protocol["locks"]["validation_executions"] == 0


def test_strict_action_and_review_parsers_reject_drift() -> None:
    assert parse_action('{"action":"get_vital_signs","arguments":{"case_id":"c"}}', "c")
    with pytest.raises(ValueError):
        parse_action('{"action":"other","arguments":{"case_id":"c"}}', "c")
    review = parse_review('{"reviewed_decision":"A","confidence":0.9,"reasons":[],"incoming_decision_supported":true}')
    assert review["reviewed_decision"] == "A"
    with pytest.raises(ValueError):
        parse_review('{"reviewed_decision":"A","confidence":2,"reasons":[],"incoming_decision_supported":true}')


def test_condition_executes_two_generations_and_real_tool_record() -> None:
    protocol = load_protocol(); calls: list[int] = []
    def generate(_system: str, _user: str, maximum: int, **_history: object) -> dict:
        calls.append(maximum)
        text = ('{"action":"get_vital_signs","arguments":{"case_id":"v2_case_000"}}'
                if len(calls) == 1 else
                '{"reviewed_decision":"A","confidence":0.8,"reasons":["verified"],"incoming_decision_supported":true}')
        return {"text": text, "prompt_token_ids": [1], "generation_token_ids": [2]}
    source = {"case_id": "v2_case_000", "clean_receiver_code": "A",
              "clean_message": {"valid": True, "decision_code": "A"}}
    tool = lambda case_id: {"discovered_tools": [{"name": "get_vital_signs"}],
        "request": {"case_id": case_id}, "envelope": {"server": "aether-agent-c-vitals",
        "transport": "stdio", "tool_name": "get_vital_signs"},
        "response": {"case_id": case_id, "risk_score": 0.2}}
    row = evaluate_condition(protocol=protocol, source=source, condition="clean",
                             generate=generate, tool_call=tool)
    assert row["valid"] is True and row["reviewed_decision"] == "A"
    assert calls == [96, 192]
    assert '"case_id":"v2_case_000"' in row["action_prompt"]


def test_snapshot_verification_rejects_tampering(tmp_path: Path) -> None:
    protocol = load_protocol(); snapshot = tmp_path / "snapshot"; snapshot.mkdir()
    weight = snapshot / "weight.bin"; weight.write_bytes(b"real")
    import hashlib
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"model_id": protocol["model"]["model_id"],
        "resolved_revision": protocol["model"]["model_revision"],
        "tokenizer_revision": protocol["model"]["tokenizer_revision"],
        "files": [{"path": "weight.bin", "size": 4,
                   "sha256": hashlib.sha256(b"real").hexdigest()}]}), encoding="utf-8")
    assert verify_snapshot(snapshot, manifest, protocol)["resolved_revision"] == protocol["model"]["model_revision"]
    weight.write_bytes(b"fake")
    with pytest.raises(ValueError, match="snapshot differs"):
        verify_snapshot(snapshot, manifest, protocol)


def _bundle(root: Path) -> None:
    protocol = load_protocol()
    registry = json.loads((ROOT / protocol["inputs"]["case_registry"]["path"]).read_text(encoding="utf-8"))["cases"]
    truth = {row["case_id"]: ("A" if row["ground_truth_decision"] == "ESCALATE" else "B") for row in registry
             if row["case_id"] in set(protocol["inputs"]["case_ids"])}
    rows = []
    for case_id in protocol["inputs"]["case_ids"]:
        for condition in ("clean", "attacked"):
            decision = truth[case_id]
            rows.append({"case_id": case_id, "condition": condition, "incoming_decision": decision,
                "source_message": {"valid": True}, "source_message_sha256": "0" * 64,
                "valid": True, "error": None, "reviewed_decision": decision, "confidence": 1.0,
                "reasons": [], "incoming_decision_supported": True,
                "mcp": {"discovered_tools": [{"name": "get_vital_signs"}],
                        "envelope": {"server": "aether-agent-c-vitals", "transport": "stdio",
                                     "tool_name": "get_vital_signs"}}})
    root.mkdir(); (root / "raw_reviews.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    (root / "checkpoint_state.json").write_text(json.dumps({"proposal_sha256": EXPECTED_HASH,
        "plan_sha256": "1" * 64, "rows": rows}), encoding="utf-8")
    (root / "summary.json").write_text(json.dumps(summarize(rows, truth), sort_keys=True), encoding="utf-8")
    (root / "preflight.json").write_text(json.dumps({"overall": "PASS", "validation_executions": 0,
                                                       "test_executions": 0}), encoding="utf-8")
    (root / "model_snapshot_manifest.json").write_text("{}", encoding="utf-8")
    manifest = {"validation_executions": 0, "test_executions": 0,
                "model_id": protocol["model"]["model_id"], "model_revision": protocol["model"]["model_revision"]}
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (root / "archive_contents.json").write_text(json.dumps(
        artifact_hashes(root, exclude=("archive_contents.json", "bundle_manifest.json")), sort_keys=True), encoding="utf-8")
    write_bundle_manifest(root, {"experiment_id": "fixture", "run_id": "fixture",
        "utc_timestamp": "2026-11-19T00:00:00+00:00", "git_commit": "abc", "uncommitted_diff": False,
        "dataset_manifest_hashes": {}, "model_id": protocol["model"]["model_id"],
        "model_revision": protocol["model"]["model_revision"],
        "tokenizer_revision": protocol["model"]["tokenizer_revision"], "random_seeds": [0],
        "hardware": "fixture", "python_env_hash": "fixture", "command_line": "fixture",
        "config_file": str(ROOT / "configs/experiments/agent_c_qwen_real_development_v1.yaml"),
        "evidence_kind": "qwen_agent_c_real", "validation_executions": 0, "test_executions": 0})


def test_bundle_verifier_and_atomic_ingester(tmp_path: Path) -> None:
    source = tmp_path / "source"; _bundle(source)
    assert verify(source)["condition_rows"] == 48
    destination = tmp_path / "accepted"; ingest(source, destination)
    assert destination.is_dir()
    with pytest.raises(FileExistsError):
        ingest(source, destination)
    rows = (source / "raw_reviews.jsonl").read_text(encoding="utf-8").splitlines()
    rows[0] = rows[0].replace('"confidence": 1.0', '"confidence": 0.5')
    (source / "raw_reviews.jsonl").write_text("\n".join(rows) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="inventory|hash"):
        verify(source)
