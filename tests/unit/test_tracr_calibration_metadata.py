"""Tests for bounded Tracr calibration metadata."""

import json
from hashlib import sha256
from pathlib import Path


def test_tracr_config_is_pinned_and_classified_narrowly() -> None:
    config = json.loads(Path("calibration/tracr/config.json").read_text(encoding="utf-8"))
    assert config["revision"] == "9ce2b8c82b6ba10e62e86cf6f390e7536d4fd2cd"
    assert config["license"] == "Apache-2.0"
    assert config["program"] == "tracr.compiler.lib.make_reverse(rasp.tokens)"
    assert config["environment"] == ".venv-tracr"


def test_completed_tracr_manifest_integrity() -> None:
    manifest_path = Path("results/calibration/tracr/manifest.json")
    if not manifest_path.exists():
        return
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for path_key, hash_key in (
        ("config_path", "config_sha256"),
        ("result_path", "result_sha256"),
        ("environment_path", "environment_sha256"),
    ):
        path = Path(manifest[path_key])
        assert path.exists()
        assert sha256(path.read_bytes()).hexdigest() == manifest[hash_key]
