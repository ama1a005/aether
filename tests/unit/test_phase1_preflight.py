import sys

import yaml

from scripts import phase1_preflight


def test_preflight_is_model_free_and_fail_closed(monkeypatch, tmp_path):
    config = {"minimum_ram_gib": 0, "minimum_available_ram_gib": 0,
              "minimum_disk_free_gib": 0, "require_cuda": False,
              "packages": {}, "model": {"id": "toy", "revision": "rev",
              "cache_path": "missing"}, "output_directories": []}
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config))
    result = phase1_preflight.inspect(path)
    assert result["model_accessed"] is False
    assert result["model"]["revision"] == "rev"
    assert result["overall"] == "BLOCKED"
    assert result["checks"]["python_3_11"] == (sys.version_info[:2] == (3, 11))
