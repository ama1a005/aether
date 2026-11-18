"""Tests for verified causal-core statistical reporting."""

import json

import pytest

from evaluation.causal_core_report import exact_mcnemar, generate, wilson


def test_wilson_and_exact_mcnemar_known_values() -> None:
    low, high = wilson(8, 8)
    assert low == pytest.approx(0.6755924351)
    assert high == pytest.approx(1.0)
    assert exact_mcnemar(0, 8) == pytest.approx(0.0078125)
    assert exact_mcnemar(0, 0) == 1.0


def test_repository_causal_core_report_uses_verified_artifacts(tmp_path) -> None:
    json_path, markdown_path = generate(tmp_path / "report")
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["overall"] == "PASS"
    assert payload["metrics"]["once_only_test"]["repair_attacked_correct"] == 8
    assert payload["metrics"]["once_only_test"]["baseline_attacked_correct"] == 0
    assert payload["metrics"]["once_only_test"]["mcnemar_exact_two_sided_p"] == pytest.approx(0.0078125)
    assert payload["phase1_overall_evidence"] == "INCOMPLETE"
    assert "second_model_qualification" in payload["remaining_phase1_gates"]
    assert "oracle-free deployable defense" in markdown_path.read_text(encoding="utf-8")
    assert (tmp_path / "report/causal_core_recovery.svg").read_text(encoding="utf-8").startswith("<svg")
    with pytest.raises(FileExistsError):
        generate(tmp_path / "report")
