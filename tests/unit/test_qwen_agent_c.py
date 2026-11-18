"""Tests for real-Qwen trace Agent-C review semantics."""

import json

from experiments.phase1.qwen_agent_c import evaluate


def test_agent_c_evaluator_preserves_invalid_rows_and_reviews_clean_vitals() -> None:
    registry = [{"case_id": "c", "split": "development", "features": {"spo2": 90},
                 "ground_truth_decision": "ESCALATE", "dataset_version": "v"}]
    rows = [{"case_id": "c", "eligible": True, "clean_message_valid": True,
             "attacked_message_valid": True, "clean_receiver_code": "A",
             "clean_message": {"valid": True, "decision_code": "A"},
             "attacked_receiver_code": "B",
             "attacked_message": {"valid": True, "decision_code": "B"}}]
    result = evaluate(rows, registry, 0.4)
    assert result["counts"] == {"total": 2, "valid": 2, "invalid": 0,
                                "incoming_correct": 1, "reviewed_correct": 2}
    assert {row["condition"] for row in result["rows"]} == {"clean", "attacked"}


def test_agent_c_rejects_validation_rows_and_duplicate_case_ids() -> None:
    registry = [{"case_id": "c", "split": "development", "features": {"spo2": 90},
                 "ground_truth_decision": "ESCALATE", "dataset_version": "v"},
                {"case_id": "v", "split": "validation", "features": {"spo2": 90},
                 "ground_truth_decision": "ESCALATE", "dataset_version": "v"}]
    row = {"case_id": "v", "eligible": True, "clean_message_valid": True,
           "attacked_message_valid": True, "clean_receiver_code": "A", "clean_message": {"valid": True},
           "attacked_receiver_code": "A", "attacked_message": {"valid": True}}
    import pytest
    with pytest.raises(ValueError, match="development registry"):
        evaluate([row], registry, 0.4)


def test_run_requires_approval_before_opening_inputs(tmp_path) -> None:
    import yaml
    import pytest
    from experiments.phase1.qwen_agent_c import run

    config = tmp_path / "proposal.yaml"
    config.write_text(yaml.safe_dump({
        "status": "awaiting_human_protocol_review", "split": "development",
        "validation_executions": 0, "test_executions": 0,
        "qwen_rows": "missing_rows.json", "case_registry": "missing_registry.json",
        "risk_score_threshold": 0.4,
    }), encoding="utf-8")
    with pytest.raises(PermissionError, match="human protocol decision is missing"):
        run(config, tmp_path / "missing_approval.json", tmp_path / "output")
    assert not (tmp_path / "output").exists()


def test_resume_requires_exact_ordered_source_backed_prefix() -> None:
    import pytest
    from experiments.phase1.qwen_agent_c import _validate_resume_rows

    registry = [{"case_id": "c", "split": "development", "features": {"spo2": 90},
                 "ground_truth_decision": "ESCALATE", "dataset_version": "v"}]
    source = [{"case_id": "c", "eligible": True, "clean_message_valid": True,
               "attacked_message_valid": True, "clean_receiver_code": "A",
               "clean_message": {"valid": True, "decision_code": "A"},
               "attacked_receiver_code": "B",
               "attacked_message": {"valid": True, "decision_code": "B"}}]
    completed = evaluate(source, registry, 0.4)["rows"]
    persisted = json.loads(json.dumps(completed))
    assert _validate_resume_rows(persisted[:1], source, registry, 0.4) == persisted[:1]

    with pytest.raises(ValueError, match="prefix"):
        _validate_resume_rows(persisted[1:], source, registry, 0.4)
    altered = [dict(persisted[0], source_row={"case_id": "c", "split": "validation"})]
    with pytest.raises(ValueError, match="source-backed"):
        _validate_resume_rows(altered, source, registry, 0.4)


def test_agent_c_retains_ineligible_paired_rows_even_when_none_are_valid() -> None:
    registry = [{"case_id": "c", "split": "development", "features": {"spo2": 90},
                 "ground_truth_decision": "ESCALATE", "dataset_version": "v"}]
    source = [{"case_id": "c", "eligible": False, "clean_message_valid": True,
               "attacked_message_valid": True, "clean_receiver_code": "A",
               "clean_message": {"valid": True}, "attacked_receiver_code": "B",
               "attacked_message": {"valid": True}}]

    result = evaluate(source, registry, 0.4)

    assert result["counts"] == {"total": 2, "valid": 0, "invalid": 2,
                                "incoming_correct": 0, "reviewed_correct": 0}
    assert all(row["error"] == "invalid_qwen_trace" for row in result["rows"])


def test_execution_paths_refuse_repository_outputs_and_overwrites(tmp_path, monkeypatch) -> None:
    import subprocess
    import pytest
    import experiments.phase1.qwen_agent_c as runner

    monkeypatch.setattr(runner, "ROOT", tmp_path / "repo")
    runner.ROOT.mkdir()
    monkeypatch.setattr(runner.subprocess, "run", lambda *args, **kwargs:
                        subprocess.CompletedProcess(args[0], 0, "", ""))
    with pytest.raises(ValueError, match="outside the source checkout"):
        runner._execution_paths(runner.ROOT / "results", resume=False)

    occupied = tmp_path / "occupied-output"
    occupied.mkdir()
    (occupied / "keep.txt").write_text("preserve", encoding="utf-8")
    with pytest.raises(FileExistsError, match="nonempty output"):
        runner._execution_paths(occupied, resume=False)
    assert (occupied / "keep.txt").read_text(encoding="utf-8") == "preserve"

    partial = tmp_path / "partial-output"
    partial.mkdir()
    (partial / "raw_reviews.json").write_text("{}", encoding="utf-8")
    (partial / "summary.json").write_text("{}", encoding="utf-8")
    assert runner._execution_paths(partial, resume=True)[0] == partial.resolve()
    (partial / "bundle_manifest.json").write_text("{}", encoding="utf-8")
    with pytest.raises(FileExistsError, match="completed or unexpected"):
        runner._execution_paths(partial, resume=True)
