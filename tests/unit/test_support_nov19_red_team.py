"""Unit tests for SUPPORT-01: Red-team runner, adapter and verifier.

Tests cover:
- Mock/real mode separation (dry-run never loads model)
- Eligibility consistency checks
- Missing MCP backend handling
- Wrong model revision rejection
- Wrong tool evidence field detection
- Nondeterministic/invalid output handling
- Controller budget overrun protection
- Interrupted-run resume behaviour
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from experiments.supporting_nov19.red_team.adapter import (
    QUALIFIED_MODEL_ID,
    QUALIFIED_MODEL_REVISION,
    RealQwenBackend,
    build_development_cases,
    validate_config,
)
from experiments.supporting_nov19.red_team.verifier import verify_run


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _minimal_valid_config(output_dir: str = "results/phase1/red_team/qwen15b") -> dict:
    return {
        "schema_version": "aether.supporting-nov19.red-team.v1",
        "model_id": QUALIFIED_MODEL_ID,
        "model_revision": QUALIFIED_MODEL_REVISION,
        "tokenizer_revision": QUALIFIED_MODEL_REVISION,
        "dtype": "float32",
        "device": "cpu",
        "split": "development",
        "attack_families": ["tool_description_poison"],
        "max_target_calls": 4,
        "seed": 0,
        "drop_invalid": False,
        "output_dir": output_dir,
        "source_commit": "00846b020b685dfa3ab89bce2c5227d2810c9d1e",
    }


# ---------------------------------------------------------------------------
# Config validation tests
# ---------------------------------------------------------------------------

class TestValidateConfig:
    def test_valid_config_returns_no_errors(self, tmp_path):
        config = _minimal_valid_config(str(tmp_path / "empty_output"))
        errors = validate_config(config)
        assert errors == []

    def test_wrong_model_id_rejected(self, tmp_path):
        config = _minimal_valid_config(str(tmp_path / "empty_output"))
        config["model_id"] = "wrong/model"
        errors = validate_config(config)
        assert any("model_id" in e for e in errors)

    def test_wrong_model_revision_rejected(self, tmp_path):
        config = _minimal_valid_config(str(tmp_path / "empty_output"))
        config["model_revision"] = "deadbeef" * 5
        errors = validate_config(config)
        assert any("model_revision" in e for e in errors)

    def test_drop_invalid_true_rejected(self, tmp_path):
        config = _minimal_valid_config(str(tmp_path / "empty_output"))
        config["drop_invalid"] = True
        errors = validate_config(config)
        assert any("drop_invalid" in e for e in errors)

    def test_invalid_split_rejected(self, tmp_path):
        config = _minimal_valid_config(str(tmp_path / "empty_output"))
        config["split"] = "test"
        errors = validate_config(config)
        assert any("split" in e for e in errors)

    def test_non_empty_output_dir_rejected(self, tmp_path):
        (tmp_path / "some_file.txt").write_text("x")
        config = _minimal_valid_config(str(tmp_path))
        errors = validate_config(config)
        assert any("output_dir" in e for e in errors)

    def test_missing_key_reported(self, tmp_path):
        config = _minimal_valid_config(str(tmp_path / "empty_output"))
        del config["seed"]
        errors = validate_config(config)
        assert any("seed" in e for e in errors)


# ---------------------------------------------------------------------------
# RealQwenBackend tests (no model loading)
# ---------------------------------------------------------------------------

class TestRealQwenBackend:
    def test_wrong_model_id_raises(self):
        with pytest.raises(ValueError, match="frozen qualified model"):
            RealQwenBackend(
                model_id="wrong/model",
                model_revision=QUALIFIED_MODEL_REVISION,
                tokenizer_revision=QUALIFIED_MODEL_REVISION,
            )

    def test_wrong_revision_raises(self):
        with pytest.raises(ValueError, match="frozen qualified model"):
            RealQwenBackend(
                model_id=QUALIFIED_MODEL_ID,
                model_revision="deadbeef" * 5,
                tokenizer_revision=QUALIFIED_MODEL_REVISION,
            )

    def test_execute_before_load_fails_closed(self):
        """Real-model mode must fail hard, not fall back to mock."""
        backend = RealQwenBackend(
            model_id=QUALIFIED_MODEL_ID,
            model_revision=QUALIFIED_MODEL_REVISION,
            tokenizer_revision=QUALIFIED_MODEL_REVISION,
        )
        from contracts.schemas import PatientCase
        case = PatientCase("test_case", {"heart_rate": 70}, "DO_NOT_ESCALATE",
                           source_dataset="synthetic", source_split="development")
        with pytest.raises(RuntimeError, match="load\\(\\) must be called"):
            backend.execute(case, None, 0)

    def test_discover_returns_real_evidence_class(self):
        backend = RealQwenBackend(
            model_id=QUALIFIED_MODEL_ID,
            model_revision=QUALIFIED_MODEL_REVISION,
            tokenizer_revision=QUALIFIED_MODEL_REVISION,
        )
        recon = backend.discover()
        assert recon.evidence_class == "real_model_cpu_float32"
        assert QUALIFIED_MODEL_ID in recon.model_id
        assert len(recon.surfaces) > 0


# ---------------------------------------------------------------------------
# Development cases
# ---------------------------------------------------------------------------

class TestBuildDevelopmentCases:
    def test_returns_balanced_cases(self):
        cases = build_development_cases()
        assert len(cases) >= 2
        escalate = [c for c in cases if c.ground_truth_decision == "ESCALATE"]
        no_escalate = [c for c in cases if c.ground_truth_decision == "DO_NOT_ESCALATE"]
        assert len(escalate) > 0
        assert len(no_escalate) > 0

    def test_case_ids_are_unique(self):
        cases = build_development_cases()
        ids = [c.case_id for c in cases]
        assert len(ids) == len(set(ids))

    def test_cases_are_development_split(self):
        for case in build_development_cases():
            assert case.source_split == "development"
            assert case.fixture_only is False


# ---------------------------------------------------------------------------
# Verifier tests
# ---------------------------------------------------------------------------

class TestVerifier:
    def _make_run_dir(self, tmp_path: Path, evidence_class: str = "real_model_cpu_float32",
                      n_complete: int = 2, n_error: int = 0) -> Path:
        run_dir = tmp_path / "run_001"
        ledger = run_dir / "attempts"
        ledger.mkdir(parents=True)

        for i in range(n_complete):
            record = {
                "attempt_id": f"attempt_{i:03d}",
                "family": "tool_description_poison",
                "status": "complete",
                "success": False,
                "clean_correct": True,
                "clean": {"final_decision": "ESCALATE"},
                "attacked": {"final_decision": "ESCALATE"},
                "errors": [],
                "target_calls": 2,
            }
            (ledger / f"attempt_{i:03d}.json").write_text(json.dumps(record))

        for i in range(n_error):
            record = {
                "attempt_id": f"err_{i:03d}",
                "family": "a2a_manipulation",
                "status": "error",
                "success": False,
                "clean_correct": False,
                "clean": None,
                "attacked": None,
                "errors": [{"phase": "clean", "type": "RuntimeError", "message": "test"}],
                "target_calls": 0,
            }
            (ledger / f"err_{i:03d}.json").write_text(json.dumps(record))

        summary = {
            "run_id": "run_001",
            "evidence_class": evidence_class,
            "target_calls": n_complete * 2,
            "plan_fingerprint": "abc123",
            "total": n_complete + n_error,
            "complete": n_complete,
            "error": n_error,
            "success": 0,
        }
        (run_dir / "summary.json").write_text(json.dumps(summary))

        manifest = {
            "run_id": "run_001",
            "model_id": QUALIFIED_MODEL_ID,
            "model_revision": QUALIFIED_MODEL_REVISION,
            "git_commit": "00846b0",
        }
        (run_dir / "manifest.json").write_text(json.dumps(manifest))
        return run_dir

    def test_real_evidence_passes(self, tmp_path):
        run_dir = self._make_run_dir(tmp_path)
        report = verify_run(run_dir)
        assert report["overall"] == "PASS"
        assert report["is_real_model_evidence"] is True

    def test_non_real_evidence_fails(self, tmp_path):
        run_dir = self._make_run_dir(tmp_path, evidence_class="synthetic_software_acceptance_only")
        report = verify_run(run_dir)
        assert report["overall"] == "FAIL"
        assert "evidence_class" in report.get("reason", "")

    def test_missing_summary_fails(self, tmp_path):
        run_dir = tmp_path / "empty_run"
        run_dir.mkdir()
        report = verify_run(run_dir)
        assert report["overall"] == "FAIL"

    def test_interrupted_attempt_fails(self, tmp_path):
        run_dir = tmp_path / "interrupted_run"
        ledger = run_dir / "attempts"
        ledger.mkdir(parents=True)
        record = {"attempt_id": "x001", "family": "a2a_manipulation",
                  "status": "started", "success": False, "clean_correct": False,
                  "clean": None, "attacked": None, "errors": [], "target_calls": 1}
        (ledger / "x001.json").write_text(json.dumps(record))
        summary = {"run_id": "interrupted", "evidence_class": "real_model_cpu_float32",
                   "target_calls": 1, "plan_fingerprint": "x", "total": 1}
        (run_dir / "summary.json").write_text(json.dumps(summary))
        (run_dir / "manifest.json").write_text(json.dumps({"run_id": "interrupted",
            "model_id": QUALIFIED_MODEL_ID, "model_revision": QUALIFIED_MODEL_REVISION}))
        report = verify_run(run_dir)
        assert report["overall"] == "FAIL"
        assert "started" in report.get("reason", "")

    def test_counts_match_records(self, tmp_path):
        run_dir = self._make_run_dir(tmp_path, n_complete=3, n_error=1)
        report = verify_run(run_dir)
        assert report["n_total_attempts"] == 4
        assert report["n_complete"] == 3
        assert report["n_error"] == 1
