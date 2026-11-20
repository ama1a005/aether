"""Fail-closed protocol gate for the real-Qwen red-team package."""

from pathlib import Path

import pytest

from experiments.phase1 import qwen_red_team as red_team_module
from experiments.phase1.qwen_red_team import run


ROOT = Path(__file__).resolve().parents[2]


def test_registry_selection_excludes_locked_validation_and_test_rows() -> None:
    import json

    registry = json.loads(
        (ROOT / "data/causal_v2/case_registry.json").read_text(encoding="utf-8")
    )["cases"]
    cases = red_team_module._development_cases(registry)

    assert len(cases) == 24
    assert all(case.source_split == "development" for case in cases)
    assert [case.case_id for case in cases] == [
        row["case_id"] for row in registry if row["split"] == "development"
    ]


def test_registry_selection_rejects_empty_development_cohort() -> None:
    with pytest.raises(ValueError, match="nonempty and development-only"):
        red_team_module._development_cases([
            {"case_id": "locked", "split": "validation"}
        ])


def test_campaign_acceptance_rejects_all_errors_and_zero_clean_eligibility() -> None:
    with pytest.raises(RuntimeError, match="every attempt errored"):
        red_team_module._require_usable_campaign({"overall": {
            "eligible_attempts": 48, "errors": 48, "conditional_eligible": 0,
        }})
    with pytest.raises(RuntimeError, match="no valid clean-correct"):
        red_team_module._require_usable_campaign({"overall": {
            "eligible_attempts": 48, "errors": 1, "conditional_eligible": 0,
        }})
    red_team_module._require_usable_campaign({"overall": {
        "eligible_attempts": 48, "errors": 1, "conditional_eligible": 20,
    }})


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
