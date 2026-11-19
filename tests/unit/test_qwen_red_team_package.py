"""Fail-closed protocol gate for the real-Qwen red-team package."""

from pathlib import Path

import pytest

from experiments.phase1.qwen_red_team import run
from experiments.phase1.qwen_red_team import ROOT


def test_unreviewed_red_team_config_blocks_before_snapshot_access(tmp_path) -> None:
    with pytest.raises(PermissionError, match="decision is missing"):
        run(Path("configs/experiments/qwen_red_team_development.yaml"), tmp_path / "absent-approval.json",
            tmp_path / "absent-snapshot.json", tmp_path / "output")
    assert not (tmp_path / "output").exists()


def test_red_team_registry_is_filtered_to_development_before_execution() -> None:
    """The mixed registry must never admit validation or test cases to the campaign."""
    import json
    rows = json.loads((ROOT / "data/causal_v2/case_registry.json").read_text(encoding="utf-8"))["cases"]
    development = [row for row in rows if row["split"] == "development"]
    assert len(development) == 24
    assert all(row["split"] == "development" for row in development)
