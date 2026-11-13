"""Tests for final evidence report rejection and hash indexing."""

import json

import pytest
import yaml

from evaluation.phase1_evidence_report import generate


def _config(root, prerequisite_exists: bool):
    if prerequisite_exists:
        (root / "evidence.json").write_text(json.dumps({"overall": "PASS"}), encoding="utf-8")
    config = {
        "schema_version": "aether.phase1-completion.v1", "claim_boundary": "test",
        "gates": [
            {"id": "prerequisite", "category": "test", "kind": "json", "path": "evidence.json", "expect": {"overall": "PASS"}},
            {"id": "final_verified_report", "category": "reporting", "kind": "json", "path": "final/report_manifest.json", "expect": {"overall": "PASS"}},
        ],
    }
    path = root / "config.yaml"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return path


def test_final_evidence_report_rejects_incomplete_prerequisites(tmp_path) -> None:
    with pytest.raises(ValueError, match="incomplete"):
        generate(tmp_path, _config(tmp_path, False), tmp_path / "final")


def test_final_evidence_report_hashes_verified_inputs(tmp_path) -> None:
    destination = generate(tmp_path, _config(tmp_path, True), tmp_path / "final")
    payload = json.loads(destination.read_text(encoding="utf-8"))
    assert payload["overall"] == "PASS" and payload["incomplete_runs_rejected"] is True
    assert len(payload["evidence"]["prerequisite"]["hashes"]) == 1
    with pytest.raises(FileExistsError):
        generate(tmp_path, tmp_path / "config.yaml", tmp_path / "final")
