"""Integration tests for SUPPORT-02: Agent C review study."""
from __future__ import annotations

import pytest

from contracts.schemas import A2AMessageRecord, PatientCase
from target.agents.agent_a import AgentA
from target.agents.agent_b import AgentB
from target.agents.agent_c import AgentC
from target.three_agent_pipeline import run_three_agent_pipeline
from experiments.supporting_nov19.agent_c.runner import validate_agent_c_config
from experiments.supporting_nov19.red_team.adapter import (
    QUALIFIED_MODEL_ID,
    QUALIFIED_MODEL_REVISION,
)



@pytest.mark.integration
class TestAgentCPipelineIntegration:
    """Integration tests using rule agents (no real model)."""

    def test_three_agent_pipeline_runs_without_real_model(self):
        """Confirm pipeline structure is callable with rule agents."""
        from target.mcp.mock_client import MockMCPClient
        from target.mcp.tools import get_ecg_analysis, get_vital_signs

        mcp = MockMCPClient()
        mcp.register_tool("get_ecg_analysis", get_ecg_analysis)
        mcp.register_tool("get_vital_signs", get_vital_signs)
        agent_a = AgentA("rule_agent_a", mcp, {})
        agent_b = AgentB("rule_agent_b", {})
        agent_c = AgentC("rule_agent_c", {"use_verification_tool": False})

        case = PatientCase(
            case_id="int_test_001",
            features={"heart_rate": 130, "rhythm": "irregular"},
            ground_truth_decision="ESCALATE",
            source_dataset="synthetic",
            source_split="development",
        )
        result = run_three_agent_pipeline(case, agent_a, agent_b, agent_c)
        assert result.agent_b_decision in {"ESCALATE", "DO_NOT_ESCALATE"}
        assert result.review.reviewed_decision in {"ESCALATE", "DO_NOT_ESCALATE"}
        assert result.review.incoming_decision == result.agent_b_decision

    def test_agent_c_does_not_overwrite_agent_b_raw_output(self):
        """Agent C review must not silently alter Agent B's logged raw decision."""
        from target.mcp.mock_client import MockMCPClient
        from target.mcp.tools import get_ecg_analysis, get_vital_signs

        mcp = MockMCPClient()
        mcp.register_tool("get_ecg_analysis", get_ecg_analysis)
        mcp.register_tool("get_vital_signs", get_vital_signs)
        agent_a = AgentA("rule_agent_a", mcp, {})
        agent_b = AgentB("rule_agent_b", {})
        agent_c = AgentC("rule_agent_c", {"use_verification_tool": False})

        case = PatientCase(
            case_id="int_test_002",
            features={"heart_rate": 65, "rhythm": "normal"},
            ground_truth_decision="DO_NOT_ESCALATE",
            source_dataset="synthetic",
            source_split="development",
        )
        result = run_three_agent_pipeline(case, agent_a, agent_b, agent_c)
        # Agent B's raw decision is preserved in ThreeAgentResult
        assert result.agent_b_decision in {"ESCALATE", "DO_NOT_ESCALATE"}
        # Agent C's reviewed_decision is separate
        assert result.review.incoming_decision == result.agent_b_decision

    def test_dry_run_mode_does_not_import_model(self, tmp_path):
        """dry_run() must return 0 without loading model weights."""
        import json
        config = {
            "schema_version": "aether.supporting-nov19.agent-c.v1",
            "model_id": QUALIFIED_MODEL_ID,
            "model_revision": QUALIFIED_MODEL_REVISION,
            "tokenizer_revision": QUALIFIED_MODEL_REVISION,
            "dtype": "float32",
            "device": "cpu",
            "seed": 0,
            "agent_c_config": {"use_verification_tool": False},
            "output_dir": str(tmp_path / "out"),
            "source_commit": "00846b020b685dfa3ab89bce2c5227d2810c9d1e",
        }
        config_path = tmp_path / "agent_c_test.json"
        config_path.write_text(json.dumps(config), encoding="utf-8")

        from experiments.supporting_nov19.agent_c.runner import dry_run
        rc = dry_run(config_path)
        assert rc == 0
