"""Tests for atomic QCI-2A1 ingestion."""

from __future__ import annotations

import pytest

from scripts.ingest_qci2_audit_bundle import ingest


def test_qci2_audit_ingest_refuses_existing_destination(tmp_path) -> None:
    source = tmp_path / "source"; source.mkdir()
    destination = tmp_path / "destination"; destination.mkdir()
    with pytest.raises(FileExistsError, match="already exists"):
        ingest(source, destination)
