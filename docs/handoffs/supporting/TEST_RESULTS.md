# TEST_RESULTS.md — Supporting Experiment Test Output

**Branch:** `amala`  
**Date:** 2026-11-13  
**Exit code:** 0 (all tests passed)

## Supporting Tests (50 tests)

```
============================= test session starts =============================
platform win32 -- Python 3.11.4, pytest-8.4.1, pluggy-1.6.0 -- C:\Users\amala\AppData\Local\Programs\Python\Python311\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\amala\.gemini\antigravity\scratch\aether
configfile: pyproject.toml
plugins: anyio-4.12.1, langsmith-0.7.17, asyncio-1.1.0
asyncio: mode=Mode.STRICT, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 50 items

tests/unit/test_support_nov19_red_team.py::TestValidateConfig::test_valid_config_returns_no_errors PASSED [  2%]
tests/unit/test_support_nov19_red_team.py::TestValidateConfig::test_wrong_model_id_rejected PASSED [  4%]
tests/unit/test_support_nov19_red_team.py::TestValidateConfig::test_wrong_model_revision_rejected PASSED [  6%]
tests/unit/test_support_nov19_red_team.py::TestValidateConfig::test_drop_invalid_true_rejected PASSED [  8%]
tests/unit/test_support_nov19_red_team.py::TestValidateConfig::test_invalid_split_rejected PASSED [ 10%]
tests/unit/test_support_nov19_red_team.py::TestValidateConfig::test_non_empty_output_dir_rejected PASSED [ 12%]
tests/unit/test_support_nov19_red_team.py::TestValidateConfig::test_missing_key_reported PASSED [ 14%]
tests/unit/test_support_nov19_red_team.py::TestRealQwenBackend::test_wrong_model_id_raises PASSED [ 16%]
tests/unit/test_support_nov19_red_team.py::TestRealQwenBackend::test_wrong_revision_raises PASSED [ 18%]
tests/unit/test_support_nov19_red_team.py::TestRealQwenBackend::test_execute_before_load_fails_closed PASSED [ 20%]
tests/unit/test_support_nov19_red_team.py::TestRealQwenBackend::test_discover_returns_real_evidence_class PASSED [ 22%]
tests/unit/test_support_nov19_red_team.py::TestBuildDevelopmentCases::test_returns_balanced_cases PASSED [ 24%]
tests/unit/test_support_nov19_red_team.py::TestBuildDevelopmentCases::test_case_ids_are_unique PASSED [ 26%]
tests/unit/test_support_nov19_red_team.py::TestBuildDevelopmentCases::test_cases_are_development_split PASSED [ 28%]
tests/unit/test_support_nov19_red_team.py::TestVerifier::test_real_evidence_passes PASSED [ 30%]
tests/unit/test_support_nov19_red_team.py::TestVerifier::test_non_real_evidence_fails PASSED [ 32%]
tests/unit/test_support_nov19_red_team.py::TestVerifier::test_missing_summary_fails PASSED [ 34%]
tests/unit/test_support_nov19_red_team.py::TestVerifier::test_interrupted_attempt_fails PASSED [ 36%]
tests/unit/test_support_nov19_red_team.py::TestVerifier::test_counts_match_records PASSED [ 38%]
tests/unit/test_support_nov19_agent_c.py::TestValidateAgentCConfig::test_valid_config_passes PASSED [ 40%]
tests/unit/test_support_nov19_agent_c.py::TestValidateAgentCConfig::test_wrong_model_id_rejected PASSED [ 42%]
tests/unit/test_support_nov19_agent_c.py::TestValidateAgentCConfig::test_wrong_model_revision_rejected PASSED [ 44%]
tests/unit/test_support_nov19_agent_c.py::TestValidateAgentCConfig::test_missing_agent_c_config_rejected PASSED [ 46%]
tests/unit/test_support_nov19_agent_c.py::TestValidateAgentCConfig::test_missing_output_dir_rejected PASSED [ 48%]
tests/unit/test_support_nov19_agent_c.py::TestAgentCReviewOutcome::test_agent_c_escalates_on_critical_risk PASSED [ 50%]
tests/unit/test_support_nov19_agent_c.py::TestAgentCReviewOutcome::test_agent_c_preserves_escalation PASSED [ 52%]
tests/unit/test_support_nov19_agent_c.py::TestAgentCReviewOutcome::test_agent_c_rejects_invalid_incoming_decision PASSED [ 54%]
tests/unit/test_support_nov19_sae.py::TestValidateSaeConfig::test_valid_config_passes PASSED [ 56%]
tests/unit/test_support_nov19_sae.py::TestValidateSaeConfig::test_wrong_model_id_rejected PASSED [ 58%]
tests/unit/test_support_nov19_sae.py::TestValidateSaeConfig::test_missing_component_id_rejected PASSED [ 60%]
tests/unit/test_support_nov19_sae.py::TestQCI2Candidates::test_four_candidates_declared PASSED [ 62%]
tests/unit/test_support_nov19_sae.py::TestQCI2Candidates::test_candidate_ids_are_strings PASSED [ 64%]
tests/unit/test_support_nov19_sae.py::TestExternalArchiveNote::test_sha256_is_declared PASSED [ 66%]
tests/unit/test_support_nov19_sae.py::TestLinearSAEContract::test_load_valid_checkpoint PASSED [ 68%]
tests/unit/test_support_nov19_sae.py::TestLinearSAEContract::test_reconstruction_roundtrip PASSED [ 70%]
tests/unit/test_support_nov19_sae.py::TestLinearSAEContract::test_wrong_model_id_rejected PASSED [ 72%]
tests/unit/test_support_nov19_second_model.py::TestValidateSecondModelConfig::test_valid_config_passes PASSED [ 74%]
tests/unit/test_support_nov19_second_model.py::TestValidateSecondModelConfig::test_primary_model_as_second_rejected PASSED [ 76%]
tests/unit/test_support_nov19_second_model.py::TestValidateSecondModelConfig::test_disqualified_model_rejected PASSED [ 78%]
tests/unit/test_support_nov19_second_model.py::TestValidateSecondModelConfig::test_unknown_model_revision_rejected PASSED [ 80%]
tests/unit/test_support_nov19_second_model.py::TestValidateSecondModelConfig::test_empty_model_revision_rejected PASSED [ 82%]
tests/unit/test_support_nov19_second_model.py::TestValidateSecondModelConfig::test_missing_output_dir_rejected PASSED [ 84%]
tests/unit/test_support_nov19_second_model.py::TestValidateSecondModelConfig::test_qwen_05b_disqualified PASSED [ 86%]
tests/unit/test_support_nov19_second_model.py::TestDisqualifiedModelsList::test_qwen_05b_in_disqualified PASSED [ 88%]
tests/unit/test_support_nov19_second_model.py::TestDisqualifiedModelsList::test_primary_model_not_in_disqualified PASSED [ 90%]
tests/integration/test_support_nov19_red_team_integration.py::TestRedTeamIntegrationWithRuleBackend::test_campaign_runs_with_rule_backend PASSED [ 92%]
tests/integration/test_support_nov19_red_team_integration.py::TestRedTeamIntegrationWithRuleBackend::test_verifier_rejects_synthetic_evidence PASSED [ 94%]
tests/integration/test_support_nov19_agent_c_integration.py::TestAgentCPipelineIntegration::test_three_agent_pipeline_runs_without_real_model PASSED [ 96%]
tests/integration/test_support_nov19_agent_c_integration.py::TestAgentCPipelineIntegration::test_agent_c_does_not_overwrite_agent_b_raw_output PASSED [ 98%]
tests/integration/test_support_nov19_agent_c_integration.py::TestAgentCPipelineIntegration::test_dry_run_mode_does_not_import_model PASSED [100%]

============================== warnings summary ===============================
tests\integration\test_support_nov19_red_team_integration.py:18
  C:\Users\amala\.gemini\antigravity\scratch\aether\tests\integration\test_support_nov19_red_team_integration.py:18: PytestUnknownMarkWarning: Unknown pytest.mark.integration - is this a typo?  You can register custom marks to avoid this warning - for details, see https://docs.pytest.org/en/stable/how-to/mark.html
    @pytest.mark.integration

tests\integration\test_support_nov19_agent_c_integration.py:19
  C:\Users\amala\.gemini\antigravity\scratch\aether\tests\integration\test_support_nov19_agent_c_integration.py:19: PytestUnknownMarkWarning: Unknown pytest.mark.integration - is this a typo?  You can register custom marks to avoid this warning - for details, see https://docs.pytest.org/en/stable/how-to/mark.html
    @pytest.mark.integration

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================= 50 passed, 2 warnings in 19.89s =======================
```

## Core Regression Tests (50 tests)

```
50 passed in 7.75s
```

Tests verified: `test_target`, `test_attacks`, `test_agent_c`, `test_contracts`,
`test_red_team_orchestration` — all 50 passing, zero regressions.
