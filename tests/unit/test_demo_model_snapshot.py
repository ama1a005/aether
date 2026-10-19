"""Integrity checks for offline pinned-model transfer."""
from __future__ import annotations
import pytest

from scripts.model_snapshot_manifest import create, verify

def _snapshot(root) -> None:
    (root / "config.json").write_text("{}", encoding="utf-8")
    (root / "tokenizer.json").write_text("{}", encoding="utf-8")
    (root / "tokenizer_config.json").write_text("{}", encoding="utf-8")
    (root / "generation_config.json").write_text("{}", encoding="utf-8")
    (root / "model.safetensors").write_bytes(b"weights")

def test_snapshot_manifest_round_trip(tmp_path) -> None:
    _snapshot(tmp_path)
    payload = create(tmp_path)
    assert payload["resolved_revision"] == "7ae557604adf67be50417f59c2c2f167def9a775"
    assert verify(tmp_path) == payload

def test_snapshot_manifest_rejects_changed_weight(tmp_path) -> None:
    _snapshot(tmp_path)
    create(tmp_path)
    (tmp_path / "model.safetensors").write_bytes(b"changed")
    with pytest.raises(ValueError, match="integrity failure"):
        verify(tmp_path)
