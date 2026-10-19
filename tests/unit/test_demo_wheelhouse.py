"""Integrity tests for the ignored offline wheelhouse workflow."""

from __future__ import annotations

import json

import pytest

from scripts.wheelhouse_manifest import create_manifest, verify_manifest


def test_wheelhouse_manifest_create_and_verify(tmp_path) -> None:
    (tmp_path / "mcp-2.3.0-py3-none-any.whl").write_bytes(b"mcp-wheel")
    (tmp_path / "torch-2.8.0+cu126-cp311-cp311-win_amd64.whl").write_bytes(b"torch-wheel")
    payload = create_manifest(tmp_path)
    assert payload["python"] == "CPython 3.11"
    assert payload["platform"] == "Windows x86_64"
    assert len(payload["files"]) == 2
    assert verify_manifest(tmp_path) == payload
    manifest = json.loads((tmp_path / "wheelhouse_manifest.json").read_text(encoding="utf-8"))
    torch = next(record for record in manifest["files"] if record["package"] == "torch")
    assert torch["source_index"] == "https://download.pytorch.org/whl/cu126"


def test_wheelhouse_manifest_rejects_tampering(tmp_path) -> None:
    wheel = tmp_path / "mcp-2.3.0-py3-none-any.whl"
    wheel.write_bytes(b"original")
    create_manifest(tmp_path)
    wheel.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="integrity failure"):
        verify_manifest(tmp_path)
