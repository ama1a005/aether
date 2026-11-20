"""Official MCP SDK stdio server exposing source-attributed review tools."""

from __future__ import annotations

from typing import Any, Callable

try:
    from mcp.server.mcpserver import MCPServer as FastMCP
except ImportError:
    from mcp.server.fastmcp import FastMCP

from demo.backend.repository import get_case
from demo.backend.tools import TOOLS

SERVER_NAME = "aether-clinical-tools"
mcp = FastMCP(
    SERVER_NAME,
    instructions="PTB-XL-derived AETHER review data only; never use for clinical care.",
)


def _execute(case_id: str, tool_name: str) -> dict[str, Any]:
    case = get_case(case_id)
    response = TOOLS[tool_name](case)
    return {
        "schema_version": "aether.demo.mcp-tool-result.v1",
        "server": SERVER_NAME,
        "transport": "stdio",
        "tool_name": tool_name,
        "case_id": case_id,
        "dataset_origin": case.dataset_origin,
        "provenance": "PTB-XL-DERIVED DEMONSTRATION VIA REAL MCP",
        "source_record_id": case.provenance["source_record_id"],
        "response": response,
    }


def _register(tool_name: str, description: str) -> Callable[[str], dict[str, Any]]:
    def tool(case_id: str) -> dict[str, Any]:
        return _execute(case_id, tool_name)

    tool.__name__ = tool_name
    tool.__doc__ = description
    mcp.tool(name=tool_name)(tool)
    return tool


patient_record = _register("patient_record", "Return available PTB-XL-derived patient metadata; unavailable fields are explicit.")
ecg_analysis = _register("ecg_analysis", "Return PTB-XL diagnostic metadata and the disclosed AETHER action.")
lab_results = _register("lab_results", "Return an explicit unavailable marker because PTB-XL supplies no lab values.")
vitals_monitor = _register("vitals_monitor", "Return an explicit unavailable marker because PTB-XL supplies no vital signs.")
medication_safety = _register("medication_safety", "Return an explicit unavailable marker; not used by the active cohort.")
allergy_check = _register("allergy_check", "Return an explicit unavailable marker; not used by the active cohort.")
neuro_assessment = _register("neuro_assessment", "Return an explicit unavailable marker; not used by the active cohort.")
risk_assessment = _register("risk_assessment", "Return the disclosed AETHER-derived demonstration action.")


def main() -> None:
    """Serve MCP over process stdin/stdout; stdout is reserved for the protocol."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
