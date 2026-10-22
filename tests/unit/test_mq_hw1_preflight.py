"""The portable preflight must decide only from measured resources and frozen config."""

import json
from pathlib import Path
from types import SimpleNamespace

from scripts import check_mq_hw1


def test_preflight_records_no_model_access_and_frozen_hash(monkeypatch, tmp_path: Path) -> None:
    gate = {
        "candidate_model_id": "Qwen/Qwen2.5-1.5B-Instruct",
        "minimum_installed_physical_ram_gib": 15.0,
        "minimum_pre_access_available_physical_ram_gib": 10.5,
        "minimum_cache_drive_free_disk_gib": 12.0,
        "execution": {"device": "cpu", "dtype": "float32", "quantized": False,
                      "explicit_offload": False, "disk_offload": False,
                      "cuda_install_or_migration": False, "page_file_modification": False},
        "split_access_policy": {"validation": "forbidden", "test": "forbidden"},
        "pre_access_failure_state": "BLOCKED_PRE_ACCESS",
    }
    gate_path = tmp_path / "gate.json"
    gate_path.write_text(json.dumps(gate), encoding="utf-8")
    monkeypatch.setattr(check_mq_hw1.psutil, "virtual_memory",
                        lambda: SimpleNamespace(total=16 * 2**30, available=11 * 2**30))
    monkeypatch.setattr(check_mq_hw1.shutil, "disk_usage",
                        lambda path: SimpleNamespace(free=13 * 2**30))
    result = check_mq_hw1.measure(gate_path, tmp_path)
    assert result["decision"]["overall"] == "PASS"
    assert result["model_accessed"] is False
    assert len(result["gate_sha256"]) == 64
    assert result["measurements"] == {
        "installed_ram_gib": 16.0, "available_ram_gib": 11.0, "disk_free_gib": 13.0}


def test_preflight_blocks_before_model_access(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(check_mq_hw1.psutil, "virtual_memory",
                        lambda: SimpleNamespace(total=16 * 2**30, available=2 * 2**30))
    monkeypatch.setattr(check_mq_hw1.shutil, "disk_usage",
                        lambda path: SimpleNamespace(free=20 * 2**30))
    result = check_mq_hw1.measure(check_mq_hw1.DEFAULT_GATE, tmp_path)
    assert result["decision"]["state"] == "BLOCKED_PRE_ACCESS"
    assert result["model_accessed"] is False
