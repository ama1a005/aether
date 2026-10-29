"""Red-team backend executes clean evidence through real MCP stdio."""
from demo.backend.red_team_backend import DemoMCPRuleBackend
from contracts.schemas import PatientCase


def test_rule_backend_uses_real_mcp_discovery_and_calls():
    backend = DemoMCPRuleBackend()
    recon = backend.discover()
    assert recon.backend_id.endswith("official_mcp_sdk_stdio")
    assert {tool["name"] for tool in recon.tools} >= {"ecg_analysis", "vitals_monitor"}
    case = PatientCase("DEMO-PAT-001", {}, "ESCALATE", source_dataset="synthetic",
                       fixture_only=True)
    trace = backend.execute(case, None, 0)
    assert trace.tool_calls[0]["result"]["recommendation_code"] in {"A", "B"}
    assert trace.final_decision in {"ESCALATE", "DO_NOT_ESCALATE"}
