"""Real stdio transport acceptance for the approved Agent C tool."""

from pathlib import Path

from target.mcp.agent_c_client import call_vital_signs


def test_agent_c_discovers_and_calls_real_mcp_stdio() -> None:
    registry = Path(__file__).resolve().parents[2] / "data/causal_v2/case_registry.json"
    result = call_vital_signs(registry, "v2_case_000")
    assert result["envelope"]["transport"] == "stdio"
    assert result["response"]["case_id"] == "v2_case_000"
    assert "ground_truth_decision" not in result["response"]
