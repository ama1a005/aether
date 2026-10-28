"""Unit tests for mandatory Agent C policy review."""

from contracts.schemas import A2AMessageRecord, PatientCase
from target.agents.agent_c import AgentC
from target.mcp.mock_client import MockMCPClient
from target.mcp.tools import get_vital_signs
import pytest


def message(risk="LOW", flags=None):
    return A2AMessageRecord("m", "r", "a", "b", "review", {"risk_level": risk,
                            "risk_flags": flags or []})


def case(**features):
    return PatientCase("c", features, "ESCALATE", source_dataset="synthetic")


def test_agent_c_preserves_escalation_and_escalates_critical_mediator():
    agent = AgentC("c", {})
    assert agent.run("ESCALATE", message(), case()).reviewed_decision == "ESCALATE"
    outcome = agent.run("DO_NOT_ESCALATE", message("CRITICAL"), case())
    assert outcome.reviewed_decision == "ESCALATE"
    assert outcome.reasons == ("mediator_critical_risk",)


def test_agent_c_verification_tool_is_explicit_clean_and_auditable():
    mcp = MockMCPClient()
    mcp.register_tool("get_vital_signs", get_vital_signs)
    agent = AgentC("c", {"use_verification_tool": True, "risk_score_threshold": 0.4}, mcp)
    outcome = agent.run("DO_NOT_ESCALATE", message(), case(spo2=90))
    assert outcome.reviewed_decision == "ESCALATE"
    assert outcome.reasons == ("verification_vitals_high_risk",)
    assert outcome.tool_calls[0]["result"]["risk_score"] == 0.4


def test_agent_c_does_not_consult_ground_truth():
    agent = AgentC("c", {})
    first = agent.run("DO_NOT_ESCALATE", message(), case())
    changed_truth = PatientCase("c", {}, "DO_NOT_ESCALATE", source_dataset="synthetic")
    second = agent.run("DO_NOT_ESCALATE", message(), changed_truth)
    assert first == second


def test_agent_c_configuration_and_input_fail_closed():
    with pytest.raises(ValueError, match="MCP client"):
        AgentC("c", {"use_verification_tool": True})
    with pytest.raises(ValueError, match="threshold"):
        AgentC("c", {"risk_score_threshold": 2})
    with pytest.raises(ValueError, match="invalid decision"):
        AgentC("c", {}).run("UNKNOWN", message(), case())
