"""Fail-closed protocol gate for the real-Qwen red-team package."""

from pathlib import Path

import pytest

from experiments.phase1.qwen_red_team import run


def test_unreviewed_red_team_config_blocks_before_snapshot_access(tmp_path) -> None:
    with pytest.raises(PermissionError, match="decision is missing"):
        run(Path("configs/experiments/qwen_red_team_development.yaml"), tmp_path / "absent-approval.json",
            tmp_path / "absent-snapshot.json", tmp_path / "output")
    assert not (tmp_path / "output").exists()
