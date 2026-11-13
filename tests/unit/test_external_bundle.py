"""Tests for strict external evidence bundle promotion."""

from __future__ import annotations

from datetime import datetime, timezone
import json

import pytest

from experiments.external_bundle import ingest_bundle, verify_bundle, write_bundle_manifest


def _metadata() -> dict:
    return {
        "experiment_id": "P0_external_20261114_fixture_0", "run_id": "run",
        "utc_timestamp": datetime.now(timezone.utc).isoformat(), "git_commit": "abc",
        "uncommitted_diff": False, "dataset_manifest_hashes": {"fixture": "hash"},
        "model_id": "model", "model_revision": "rev", "tokenizer_revision": "rev",
        "random_seeds": [0], "hardware": "fixture", "python_env_hash": "env",
        "command_line": "fixture", "config_file": "fixture.yaml",
        "evidence_kind": "fixture", "validation_executions": 0, "test_executions": 0,
    }


def test_bundle_verifies_and_ingests_atomically(tmp_path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "raw.json").write_text(json.dumps({"value": 1}), encoding="utf-8")
    write_bundle_manifest(source, _metadata())
    assert verify_bundle(source, expected_kind="fixture").artifact_count == 1
    destination = tmp_path / "accepted"
    ingest_bundle(source, destination, expected_kind="fixture")
    assert verify_bundle(destination).run_id == "run"
    with pytest.raises(FileExistsError):
        ingest_bundle(source, destination)


def test_bundle_rejects_tampering_dirty_source_and_protected_split(tmp_path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    raw = source / "raw.json"
    raw.write_text("{}", encoding="utf-8")
    write_bundle_manifest(source, _metadata())
    raw.write_text('{"changed":true}', encoding="utf-8")
    with pytest.raises(ValueError, match="inventory|hash"):
        verify_bundle(source)
    raw.write_text("{}", encoding="utf-8")
    manifest = json.loads((source / "bundle_manifest.json").read_text(encoding="utf-8"))
    manifest["test_executions"] = 1
    (source / "bundle_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="protected split"):
        verify_bundle(source)
