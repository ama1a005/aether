"""Model-independent tests for CORE-04 decision, verification, and ingestion."""

import json
from pathlib import Path

import pytest

from causal.remediation_freeze import sha256_file
from experiments.phase1.core04_locked_validation import ARMS, SEEDS, _authorization
from scripts.ingest_core04_validation_bundle import ingest
from scripts.verify_core04_validation_bundle import verify


def test_exact_human_approval_authorizes_implementation() -> None:
    protocol, digest = _authorization()
    assert digest == "6313d3a8d81e25be0897c6d5b986f85382303a499f524611d91abeec192868dc"
    assert protocol["review"]["model_access_before_approval"] == "forbidden"


def _bundle(root: Path) -> None:
    cases = [f"v2_case_{index:03d}" for index in range(24, 32)]
    rows = [{"evidence_type": "real_model_intervention", "split": "validation",
             "status": "ok", "arm": arm, "seed": seed, "case_id": case,
             "condition": condition}
            for seed in SEEDS for arm in ARMS for case in cases
            for condition in ("clean", "attacked")]
    artifacts = {
        "preflight.json": {"overall": "PASS", "model_accessed": False},
        "manifest.json": {"uncommitted_diff": False},
        "summary.json": {"overall": "PASS", "execution_state": "COMPLETE",
                         "scientific_outcome": "VALIDATION_ACCEPTED",
                         "raw_evaluation_count": 96, "model_forward_steps": 504,
                         "deployable_without_oracle": False,
                         "development_executions": 0, "validation_executions": 96,
                         "test_executions": 0},
        "budget_ledger.json": [{"arm": arm, "seed": seed, "state": "COMPLETE",
                                "model_forward_steps": 80 if arm == "no_defense" else 88}
                               for seed in SEEDS for arm in ARMS],
        "arm_results.json": {f"{arm}:{seed}": {"arm": arm, "seed": seed}
                             for seed in SEEDS for arm in ARMS},
        "statistics.json": {"test_gate_open": True},
    }
    for name, value in artifacts.items():
        (root / name).write_text(json.dumps(value), encoding="utf-8")
    (root / "raw_evaluations.jsonl").write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    inventory = {path.name: sha256_file(path) for path in root.iterdir() if path.is_file()}
    (root / "archive_contents.json").write_text(json.dumps(inventory), encoding="utf-8")


def test_verifier_and_ingester_accept_complete_fixture(tmp_path: Path) -> None:
    source, destination = tmp_path / "source", tmp_path / "destination"; source.mkdir(); _bundle(source)
    assert verify(source)["test_gate_open"] is True
    assert ingest(source, destination)["verification"]["raw_evaluation_count"] == 96
    with pytest.raises(FileExistsError):
        ingest(source, destination)


def test_verifier_rejects_test_access(tmp_path: Path) -> None:
    _bundle(tmp_path); raw = tmp_path / "raw_evaluations.jsonl"
    rows = raw.read_text().splitlines(); value = json.loads(rows[0]); value["split"] = "test"
    rows[0] = json.dumps(value); raw.write_text("\n".join(rows) + "\n")
    inventory = json.loads((tmp_path / "archive_contents.json").read_text())
    inventory["raw_evaluations.jsonl"] = sha256_file(raw)
    (tmp_path / "archive_contents.json").write_text(json.dumps(inventory))
    with pytest.raises(PermissionError, match="forbidden split"):
        verify(tmp_path)


def test_verifier_rejects_budget_drift(tmp_path: Path) -> None:
    _bundle(tmp_path); ledger = tmp_path / "budget_ledger.json"
    rows = json.loads(ledger.read_text()); rows[0]["model_forward_steps"] += 1
    ledger.write_text(json.dumps(rows)); inventory = json.loads((tmp_path / "archive_contents.json").read_text())
    inventory["budget_ledger.json"] = sha256_file(ledger)
    (tmp_path / "archive_contents.json").write_text(json.dumps(inventory))
    with pytest.raises(ValueError, match="504"):
        verify(tmp_path)


def test_rejected_result_keeps_test_gate_closed(tmp_path: Path) -> None:
    _bundle(tmp_path); summary = tmp_path / "summary.json"; statistics = tmp_path / "statistics.json"
    value = json.loads(summary.read_text()); value["scientific_outcome"] = "VALIDATION_REJECTED"; summary.write_text(json.dumps(value))
    statistics.write_text(json.dumps({"test_gate_open": False}))
    inventory = json.loads((tmp_path / "archive_contents.json").read_text())
    inventory["summary.json"] = sha256_file(summary); inventory["statistics.json"] = sha256_file(statistics)
    (tmp_path / "archive_contents.json").write_text(json.dumps(inventory))
    assert verify(tmp_path)["test_gate_open"] is False
