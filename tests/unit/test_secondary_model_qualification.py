"""Fail-closed tests for the generic second-model qualification package."""

import json
from pathlib import Path

import pytest

from paired_trace.run_secondary_model_qualification import prepare


def test_template_is_intentionally_blocked(tmp_path) -> None:
    with pytest.raises(ValueError, match="frozen"):
        prepare(Path("configs/model_qualification/second_model_candidate.template.json"), tmp_path / "out")


def test_secondary_package_requires_committed_reviewed_distinct_candidate(tmp_path) -> None:
    outside = tmp_path / "candidate.json"
    outside.write_text(json.dumps({}), encoding="utf-8")
    with pytest.raises(ValueError, match="committed"):
        prepare(outside, tmp_path / "out")
