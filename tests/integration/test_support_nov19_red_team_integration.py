"""Integration tests for SUPPORT-01: Red-team runner with rule-based backend."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from attacks.backends import RuleBasedBackend
from attacks.corpus.attack_store import AttackStore
from attacks.corpus.builder import CorpusBuilder
from attacks.orchestration import CampaignConfig, run_campaign
from experiments.supporting_nov19.red_team.adapter import build_development_cases
from experiments.supporting_nov19.red_team.verifier import verify_run


@pytest.mark.integration
class TestRedTeamIntegrationWithRuleBackend:
    """Integration tests using rule-based backend (no real model, labeled clearly)."""

    def test_campaign_runs_with_rule_backend(self, tmp_path):
        """Full campaign with rule backend; evidence_class is synthetic."""
        backend = RuleBasedBackend()
        campaign = CampaignConfig(
            experiment_id="SUPPORT01_integration_test",
            seed=42,
            max_target_calls=4,
            split="synthetic",
        )
        cases = build_development_cases()
        # Only use synthetic cases for rule-backend integration test
        from contracts.schemas import PatientCase
        synthetic_case = PatientCase(
            case_id="synthetic_int_001",
            features={"heart_rate": 130},
            ground_truth_decision="ESCALATE",
            source_dataset="synthetic",
            source_split="synthetic",
            fixture_only=True,
        )
        store = AttackStore(str(tmp_path / "corpus"))
        attacks = CorpusBuilder(42).build_phase1_corpus(store, 1)
        summary = run_campaign(backend, [synthetic_case], attacks, campaign,
                               tmp_path / "run_001")
        assert "total" in summary or "plan_fingerprint" in summary
        assert "evidence_class" in summary
        assert summary["evidence_class"] == "synthetic_software_acceptance_only"

    def test_verifier_rejects_synthetic_evidence(self, tmp_path):
        """Verifier must reject synthetic evidence for real_qwen gate."""
        backend = RuleBasedBackend()
        campaign = CampaignConfig(
            experiment_id="SUPPORT01_verify_rejection_test",
            seed=0,
            max_target_calls=4,
            split="synthetic",
        )
        from contracts.schemas import PatientCase
        synthetic_case = PatientCase(
            case_id="verify_test_001",
            features={"heart_rate": 110},
            ground_truth_decision="ESCALATE",
            source_dataset="synthetic",
            source_split="synthetic",
            fixture_only=True,
        )
        store = AttackStore(str(tmp_path / "corpus2"))
        attacks = CorpusBuilder(0).build_phase1_corpus(store, 1)
        run_dir = tmp_path / "run_002"
        run_campaign(backend, [synthetic_case], attacks, campaign, run_dir)
        # Verifier must FAIL for non-real evidence
        report = verify_run(run_dir)
        assert report["overall"] == "FAIL"
        assert report["is_real_model_evidence"] is False
