"""Demo-owned real-MCP adapter for the core red-team backend protocol."""
from attacks.backends import RuleBasedBackend
from attacks.orchestration import Recon
from demo.backend.mcp_client import discover_mcp_tools, run_selected_mcp_tools
from demo.backend.repository import get_case


class DemoMCPRuleBackend(RuleBasedBackend):
    """Rule agents whose clean tools execute through the official MCP SDK/stdio."""

    def __init__(self) -> None:
        def execute(name: str, inputs: dict) -> dict:
            mapped = {"get_ecg_analysis": "ecg_analysis",
                      "get_vital_signs": "vitals_monitor"}[name]
            rows = run_selected_mcp_tools(get_case(inputs["case_id"]), [mapped])
            if len(rows) != 1 or rows[0].execution_status != "COMPLETE":
                raise RuntimeError("MCP tool did not produce one complete result")
            return rows[0].response

        super().__init__(execute, "official_mcp_sdk_stdio")

    def discover(self) -> Recon:
        """Perform actual MCP initialize/list-tools before declaring support."""
        tools = tuple(discover_mcp_tools())
        names = {item["name"] for item in tools}
        if not {"ecg_analysis", "vitals_monitor"} <= names:
            raise RuntimeError("MCP server omitted required clinical tools")
        base = super().discover()
        return Recon(base.backend_id, base.model_id, base.model_revision,
                     base.tokenizer_revision, "synthetic_real_mcp_transport_acceptance",
                     base.surfaces, tools)
