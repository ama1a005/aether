"""Unit tests for SUPPORT-02: Agent C review study runner."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from experiments.supporting_nov19.agent_c.runner import validate_agent_c_config
from experiments.supporting_nov19.red_team.adapter import (
    QUALIFIED_MODEL_ID,
    QUALIFIED_MODEL_REVISION,
)


def _valid_agent_c_config(output_dir: str = "/tmp/agent_c_out") -> dict:
    return {
        "schema_version": "aether.supporting-nov19.agent-c.v1",
        "model_id": QUALIFIED_MODEL_ID,
        "model_revision": QUALIFIED_MODEL_REVISION,
        "tokenizer_revision": QUALIFIED_MODEL_REVISION,
        "dtype": "float32",
        "device": "cpu",
        "split": "development",
        "seed": 0,
        "agent_c_config": {"use_verification_tool": False, "risk_score_threshold": 0.4},
        "output_dir": output_dir,
        "source_commit": "00846b020b685dfa3ab89bce2c5227d2810c9d1e",
    }


class TestValidateAgentCConfig:
    def test_valid_config_passes(self):
        errors = validate_agent_c_config(_valid_agent_c_config())
        assert errors == []

    def test_wrong_model_id_rejected(self):
        config = _valid_agent_c_config()
        config["model_id"] = "openai/gpt-4"
        errors = validate_agent_c_config(config)
        assert any("model_id" in e for e in errors)

    def test_wrong_model_revision_rejected(self):
        config = _valid_agent_c_config()
        config["model_revision"] = "badbadba" * 5
        errors = validate_agent_c_config(config)
        assert any("model_revision" in e for e in errors)

    def test_missing_agent_c_config_rejected(self):
        config = _valid_agent_c_config()
        del config["agent_c_config"]
        errors = validate_agent_c_config(config)
        assert any("agent_c_config" in e for e in errors)

    def test_missing_output_dir_rejected(self):
        config = _valid_agent_c_config()
        del config["output_dir"]
        errors = validate_agent_c_config(config)
        assert any("output_dir" in e for e in errors)


class TestAgentCReviewOutcome:
    """Test that AgentC contract behaviour is preserved when imported."""

    def test_agent_c_escalates_on_critical_risk(self):
        from contracts.schemas import A2AMessageRecord, PatientCase
        from target.agents.agent_c import AgentC

        agent = AgentC("mock_model", {"use_verification_tool": False, "risk_score_threshold": 0.4})
        message = A2AMessageRecord(
            message_id="m1", run_id="r1", sender="agent_a", receiver="agent_b",
            content_text="critical case",
            structured_payload={"risk_level": "CRITICAL", "risk_flags": ["flag1", "flag2"]},
        )
        case = PatientCase("c1", {"heart_rate": 140}, "ESCALATE",
                           source_dataset="synthetic", source_split="development")
        outcome = agent.run("DO_NOT_ESCALATE", message, case)
        assert outcome.reviewed_decision == "ESCALATE"
        assert "mediator_critical_risk" in outcome.reasons

    def test_agent_c_preserves_escalation(self):
        from contracts.schemas import A2AMessageRecord, PatientCase
        from target.agents.agent_c import AgentC

        agent = AgentC("mock_model", {"use_verification_tool": False})
        message = A2AMessageRecord(
            message_id="m2", run_id="r2", sender="agent_a", receiver="agent_b",
            content_text="normal",
            structured_payload={"risk_level": "LOW", "risk_flags": []},
        )
        case = PatientCase("c2", {"heart_rate": 65}, "DO_NOT_ESCALATE",
                           source_dataset="synthetic", source_split="development")
        outcome = agent.run("ESCALATE", message, case)
        assert outcome.reviewed_decision == "ESCALATE"

    def test_agent_c_rejects_invalid_incoming_decision(self):
        from contracts.schemas import A2AMessageRecord, PatientCase
        from target.agents.agent_c import AgentC

        agent = AgentC("mock_model", {})
        message = A2AMessageRecord(
            message_id="m3", run_id="r3", sender="a", receiver="b", content_text="x"
        )
        case = PatientCase("c3", {}, "ESCALATE",
                           source_dataset="synthetic", source_split="development")
        with pytest.raises(ValueError, match="invalid decision"):
            agent.run("MAYBE", message, case)
