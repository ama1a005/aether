"""Fail-closed tests for the generic second-model qualification package."""

import json
from pathlib import Path
import re

import pytest

from paired_trace.run_secondary_model_qualification import prepare
from paired_trace.model_qualification import evaluate_mq_hw1


def test_template_is_intentionally_blocked(tmp_path) -> None:
    with pytest.raises(ValueError, match="frozen"):
        prepare(Path("configs/model_qualification/second_model_candidate.template.json"), tmp_path / "out")


def test_secondary_package_requires_committed_reviewed_distinct_candidate(tmp_path) -> None:
    outside = tmp_path / "candidate.json"
    outside.write_text(json.dumps({}), encoding="utf-8")
    with pytest.raises(ValueError, match="committed"):
        prepare(outside, tmp_path / "out")


def test_smollm2_is_the_one_authorized_model_for_its_derived_gate(tmp_path) -> None:
    _proposal, _candidate, hardware = prepare(
        Path("configs/model_qualification/smollm2_1_7b_second_model_freeze_v1.json"),
        tmp_path / "out",
    )
    gate = json.loads(hardware.read_text(encoding="utf-8"))
    measurement = {
        "installed_ram_gib": 31.0,
        "available_ram_gib": 29.0,
        "disk_free_gib": 100.0,
    }
    result = evaluate_mq_hw1(measurement, gate)
    assert result["predicates"]["MQ-HW1.one_model"] is True
    assert result["overall"] == "PASS"


def test_kaggle_notebook_is_ordered_and_commit_pinned() -> None:
    notebook = json.loads(Path("notebooks/aether_smollm2_second_model_qualification.ipynb").read_text(encoding="utf-8"))
    source = "\n".join("".join(cell["source"]) for cell in notebook["cells"])
    commit = re.search(r"COMMIT='([0-9a-f]{40})'", source)
    assert commit is not None
    assert source.index("--preflight-only") < source.index("snapshot_download")
    assert source.index("snapshot_download") < source.index("run_secondary_model_qualification','--output")
    assert source.index("verify_secondary_model_bundle") < source.index("tarfile.open")
