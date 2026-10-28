"""Synthetic integration test for the additive A-to-B-to-C path."""

from contracts.schemas import PatientCase
from target.agents.agent_a import AgentA
from target.agents.agent_b import AgentB
from target.agents.agent_c import AgentC
from target.mcp.mock_client import MockMCPClient
from target.mcp.tools import get_ecg_analysis, get_vital_signs
from target.three_agent_pipeline import run_three_agent_pipeline


def test_three_agent_pipeline_preserves_b_output_and_logs_c_review():
    mcp = MockMCPClient()
    mcp.register_tool("get_ecg_analysis", get_ecg_analysis)
    mcp.register_tool("get_vital_signs", get_vital_signs)
    case = PatientCase("c", {"heart_rate": 130}, "ESCALATE", source_dataset="synthetic")
    result = run_three_agent_pipeline(case, AgentA("a", mcp, {}), AgentB("b", {}),
                                      AgentC("c", {"use_verification_tool": True}, mcp))
    assert result.agent_b_decision == "ESCALATE"
    assert result.review.reviewed_decision == "ESCALATE"
    assert len(result.agent_a_tool_calls) == 2
    assert len(result.review.tool_calls) == 1
