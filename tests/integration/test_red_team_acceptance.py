"""Execute all four attack families through the actual rule-based target."""
from pathlib import Path
from experiments.phase1.red_team_smoke import run


def test_four_family_campaign(tmp_path):
    summary = run(Path("configs/experiments/red_team_synthetic.yaml"), tmp_path)
    assert len(summary["families"]) == 4
    assert summary["target_calls"] == 16
    assert summary["overall"]["errors"] == 0
    assert summary["families"]["implicit_preference_manipulation"]["successes"] == 0
    assert summary["families"]["tool_output_inject"]["successes"] == 2
