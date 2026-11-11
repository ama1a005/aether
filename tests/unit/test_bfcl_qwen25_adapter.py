"""Model-free tests for the disclosed BFCL Qwen2.5 registry adapter."""
from dataclasses import dataclass
import hashlib
import json

import pytest

from benchmarks.bfcl_qwen25 import MODEL_ID, REGISTRY_NAME, register_qwen25, verify_snapshot_manifest


@dataclass
class FakeConfig:
    model_name: str
    display_name: str
    url: str
    org: str
    license: str
    model_handler: object
    input_price: float | None
    output_price: float | None
    is_fc_model: bool
    underscore_to_dot: bool


def test_adapter_registers_without_replacing_entries():
    mapping = {"official": object()}
    handler = type("Handler", (), {})
    register_qwen25(mapping, FakeConfig, handler)
    assert mapping[REGISTRY_NAME].model_name == MODEL_ID
    assert mapping[REGISTRY_NAME].model_handler is handler
    assert "official" in mapping
    register_qwen25(mapping, FakeConfig, handler)


def test_snapshot_manifest_is_hash_and_revision_verified(tmp_path):
    revision = "abc123"
    snapshot = tmp_path / revision
    snapshot.mkdir()
    artifact = snapshot / "config.json"
    artifact.write_bytes(b"{}")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({
        "model_id": MODEL_ID,
        "resolved_revision": revision,
        "snapshot_path": str(snapshot),
        "files": [{"path": "config.json", "size": 2,
                   "sha256": hashlib.sha256(b"{}").hexdigest()}],
    }), encoding="utf-8")
    assert verify_snapshot_manifest(manifest, revision) == snapshot.resolve()
    artifact.write_bytes(b"changed")
    with pytest.raises(ValueError, match="artifact mismatch"):
        verify_snapshot_manifest(manifest, revision)
