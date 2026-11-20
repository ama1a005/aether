"""Fail-closed protocol gate for the real-Qwen red-team package."""

from pathlib import Path

import pytest

from experiments.phase1 import qwen_red_team as red_team_module
from experiments.phase1.qwen_red_team import run


def test_red_team_checkpoint_upload_retries(monkeypatch) -> None:
    class Hub:
        calls = 0

        def upload_file(self, **_arguments) -> None:
            self.calls += 1
            if self.calls < 2:
                raise OSError("temporary transport failure")

    hub = Hub()
    monkeypatch.setattr(red_team_module.time, "sleep", lambda _seconds: None)
    red_team_module._upload_with_retry(hub, path_or_fileobj="x")
    assert hub.calls == 2


def test_unreviewed_red_team_config_blocks_before_snapshot_access(tmp_path) -> None:
    with pytest.raises(PermissionError, match="decision is missing"):
        run(Path("configs/experiments/qwen_red_team_development.yaml"), tmp_path / "absent-approval.json",
            tmp_path / "absent-snapshot.json", tmp_path / "output")
    assert not (tmp_path / "output").exists()
