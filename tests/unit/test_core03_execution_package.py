"""Model-free tests for CORE-03 selection, verification and ingestion."""

from pathlib import Path
import json

import pytest

from causal.remediation_freeze import sha256_file
from experiments.phase1.core03_remediation import ARMS, SEEDS, select_arm
from scripts.ingest_core03_remediation_bundle import ingest
from scripts.verify_core03_remediation_bundle import verify


def _completed(attack: dict[str, float] | None = None) -> dict[str, dict[str, object]]:
    attack = attack or {}
    return {f"{arm}:{seed}": {
        "arm": arm, "seed": seed,
        "attacked_decision_recovery_accuracy": attack.get(arm, 1.0),
        "clean_decision_accuracy": 1.0, "invalid_or_error_count": 0,
        "model_forward_steps": 44 if "receiver" in arm else 40,
    } for seed in SEEDS for arm in ARMS}


def test_selection_is_arm_level_and_uses_frozen_complexity_tie_break() -> None:
    selected, aggregate = select_arm(_completed())
    assert selected == "fixed_receiver_l22_attention"
    assert aggregate[selected]["modified_message_units"] == 0


def test_selection_retains_complete_negative_result() -> None:
    selected, _ = select_arm(_completed({arm: 0.5 for arm in ARMS[1:]}))
    assert selected is None


def _bundle(root: Path) -> None:
    rows = [{"evidence_type": "real_model_intervention", "split": "development_audit",
             "status": "ok", "arm": arm, "seed": seed, "case_id": f"case-{case}",
             "condition": condition}
            for seed in SEEDS for arm in ARMS for case in range(4)
            for condition in ("clean", "attacked")]
    artifacts = {
        "preflight.json": {"overall": "PASS", "model_accessed": False},
        "manifest.json": {"uncommitted_diff": False},
        "summary.json": {"overall": "PASS", "execution_state": "COMPLETE",
                         "scientific_outcome": "SELECTED_DEVELOPMENT_REPAIR",
                         "selected_arm": "mechanism_receiver_l20_h5",
                         "raw_evaluation_count": 120, "deployable_without_oracle": False,
                         "validation_executions": 0, "test_executions": 0},
        "budget_ledger.json": [{"arm": arm, "seed": seed, "state": "COMPLETE",
                                "model_forward_steps": 44 if "receiver" in arm else 40}
                               for seed in SEEDS for arm in ARMS],
        "arm_results.json": _completed(), "statistics.json": {},
    }
    for name, value in artifacts.items():
        (root / name).write_text(json.dumps(value), encoding="utf-8")
    (root / "raw_evaluations.jsonl").write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8"
    )
    inventory = {path.name: sha256_file(path) for path in root.iterdir() if path.is_file()}
    (root / "archive_contents.json").write_text(json.dumps(inventory), encoding="utf-8")


def test_verifier_and_atomic_ingester_accept_complete_fixture(tmp_path: Path) -> None:
    source, destination = tmp_path / "source", tmp_path / "destination"
    source.mkdir()
    _bundle(source)
    assert verify(source)["raw_evaluation_count"] == 120
    receipt = ingest(source, destination)
    assert receipt["verification"]["overall"] == "PASS"
    with pytest.raises(FileExistsError):
        ingest(source, destination)


def test_verifier_rejects_protected_split(tmp_path: Path) -> None:
    tmp_path.mkdir(exist_ok=True)
    _bundle(tmp_path)
    raw = tmp_path / "raw_evaluations.jsonl"
    rows = raw.read_text(encoding="utf-8").splitlines()
    value = json.loads(rows[0]); value["split"] = "test"; rows[0] = json.dumps(value)
    raw.write_text("\n".join(rows) + "\n", encoding="utf-8")
    inventory = json.loads((tmp_path / "archive_contents.json").read_text())
    inventory["raw_evaluations.jsonl"] = sha256_file(raw)
    (tmp_path / "archive_contents.json").write_text(json.dumps(inventory), encoding="utf-8")
    with pytest.raises(PermissionError, match="forbidden split"):
        verify(tmp_path)
