"""Official MCP SDK stdio server exposing the eight synthetic clinical tools."""

from __future__ import annotations

from typing import Any, Callable

from mcp.server.fastmcp import FastMCP

from demo.backend.repository import get_case
from demo.backend.tools import TOOLS

SERVER_NAME = "aether-clinical-tools"
mcp = FastMCP(
    SERVER_NAME,
    instructions="Synthetic AETHER review fixtures only; never use for clinical care.",
)


def _execute(case_id: str, tool_name: str) -> dict[str, Any]:
    case = get_case(case_id)
    if tool_name not in case.available_tools:
        raise ValueError(f"tool {tool_name} is unavailable for {case_id}")
    response = TOOLS[tool_name](case)
    return {
        "schema_version": "aether.demo.mcp-tool-result.v1",
        "server": SERVER_NAME,
        "transport": "stdio",
        "tool_name": tool_name,
        "case_id": case_id,
        "dataset_origin": case.dataset_origin,
        "provenance": "SYNTHETIC DEMO FIXTURE VIA REAL MCP",
        "response": response,
    }


def _register(tool_name: str, description: str) -> Callable[[str], dict[str, Any]]:
    def tool(case_id: str) -> dict[str, Any]:
        return _execute(case_id, tool_name)

    tool.__name__ = tool_name
    tool.__doc__ = description
    mcp.tool(name=tool_name)(tool)
    return tool


patient_record = _register("patient_record", "Return synthetic history for one demo case.")
ecg_analysis = _register("ecg_analysis", "Return synthetic ECG analysis for one demo case.")
lab_results = _register("lab_results", "Return synthetic laboratory results for one demo case.")
vitals_monitor = _register("vitals_monitor", "Return synthetic vital signs for one demo case.")
medication_safety = _register("medication_safety", "Return synthetic medication safety data.")
allergy_check = _register("allergy_check", "Return synthetic allergy and airway data.")
neuro_assessment = _register("neuro_assessment", "Return a synthetic neurological screen.")
risk_assessment = _register("risk_assessment", "Return a synthetic risk score.")


def main() -> None:
    """Serve MCP over process stdin/stdout; stdout is reserved for the protocol."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
