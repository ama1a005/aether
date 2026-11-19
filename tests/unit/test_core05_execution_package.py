"""Model-independent tests for CORE-05 authorization and retained bundles."""

import json
from pathlib import Path

import pytest

from causal.remediation_freeze import sha256_file
from experiments.phase1.core05_once_only_test import ARMS, SEEDS, _authorization
from scripts.ingest_core05_test_bundle import ingest
from scripts.verify_core05_test_bundle import verify


def test_exact_approval_authorizes_core05_implementation() -> None:
    _, digest = _authorization()
    assert digest == "fc70dfedab254b428287f2d128f7eb2b521b54574f8925c3f695d562460f3c4d"


def _bundle(root: Path) -> None:
    attempt = "attempt-1"; cases = [f"v2_case_{index:03d}" for index in range(32, 40)]
    rows = [{"evidence_type": "real_model_intervention", "split": "test", "status": "ok",
             "arm": arm, "seed": seed, "case_id": case, "condition": condition}
            for seed in SEEDS for arm in ARMS for case in cases for condition in ("clean", "attacked")]
    artifacts = {
        "preflight.json": {"overall": "PASS", "model_accessed": False},
        "attempt_marker.json": {"attempt_id": attempt, "state": "COMPLETE"},
        "manifest.json": {"uncommitted_diff": False, "attempt_id": attempt},
        "summary.json": {"overall": "PASS", "execution_state": "COMPLETE", "attempt_id": attempt,
            "scientific_outcome": "TEST_ACCEPTED", "raw_evaluation_count": 96, "model_forward_steps": 504,
            "deployable_without_oracle": False, "development_executions": 0,
            "validation_executions": 0, "test_executions": 96},
        "budget_ledger.json": [{"arm": arm, "seed": seed, "state": "COMPLETE",
            "model_forward_steps": 80 if arm == "no_defense" else 88} for seed in SEEDS for arm in ARMS],
        "arm_results.json": {f"{arm}:{seed}": {} for seed in SEEDS for arm in ARMS},
        "statistics.json": {},
    }
    for name, value in artifacts.items(): (root / name).write_text(json.dumps(value), encoding="utf-8")
    (root / "raw_evaluations.jsonl").write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    inventory = {path.name: sha256_file(path) for path in root.iterdir() if path.is_file()}
    (root / "archive_contents.json").write_text(json.dumps(inventory), encoding="utf-8")


def test_verifier_and_ingester_accept_one_complete_attempt(tmp_path: Path) -> None:
    source, destination = tmp_path / "source", tmp_path / "destination"; source.mkdir(); _bundle(source)
    assert verify(source)["scientific_outcome"] == "TEST_ACCEPTED"
    assert ingest(source, destination)["verification"]["test_executions"] == 96
    with pytest.raises(FileExistsError): ingest(source, destination)


def test_verifier_rejects_attempt_identity_drift(tmp_path: Path) -> None:
    _bundle(tmp_path); summary = tmp_path / "summary.json"; value = json.loads(summary.read_text()); value["attempt_id"] = "other"; summary.write_text(json.dumps(value))
    inventory = json.loads((tmp_path / "archive_contents.json").read_text()); inventory["summary.json"] = sha256_file(summary); (tmp_path / "archive_contents.json").write_text(json.dumps(inventory))
    with pytest.raises(ValueError, match="attempt identity"): verify(tmp_path)


def test_verifier_rejects_validation_row(tmp_path: Path) -> None:
    _bundle(tmp_path); raw = tmp_path / "raw_evaluations.jsonl"; rows = raw.read_text().splitlines(); value = json.loads(rows[0]); value["split"] = "validation"; rows[0] = json.dumps(value); raw.write_text("\n".join(rows) + "\n")
    inventory = json.loads((tmp_path / "archive_contents.json").read_text()); inventory["raw_evaluations.jsonl"] = sha256_file(raw); (tmp_path / "archive_contents.json").write_text(json.dumps(inventory))
    with pytest.raises(PermissionError, match="forbidden split"): verify(tmp_path)
