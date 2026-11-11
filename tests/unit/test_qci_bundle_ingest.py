"""Tests for verified, atomic QCI evidence ingestion."""

from __future__ import annotations

import pytest

from scripts.ingest_qci_bundle import ingest
from tests.unit.test_qci_bundle_verifier import _bundle


def test_qci_ingest_verifies_and_copies_evidence(tmp_path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    _bundle(source)
    destination = tmp_path / "accepted" / "qci"
    receipt = ingest(source, destination)
    assert receipt["verification"]["overall"] == "PASS"
    assert (destination / "ingest_receipt.json").is_file()
    assert (destination / "raw_interventions.jsonl").is_file()
    assert len(receipt["copied_artifact_sha256"]) == 8


def test_qci_ingest_refuses_overwrite(tmp_path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    _bundle(source)
    destination = tmp_path / "existing"
    destination.mkdir()
    with pytest.raises(FileExistsError, match="already exists"):
        ingest(source, destination)


def test_qci_ingest_refuses_ambiguous_artifacts(tmp_path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    _bundle(source)
    nested = source / "nested"
    nested.mkdir()
    (nested / "summary.json").write_bytes((source / "summary.json").read_bytes())
    with pytest.raises(ValueError, match="duplicate artifact names"):
        ingest(source, tmp_path / "accepted")
