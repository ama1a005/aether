"""Real MCP stdio client used by the live AETHER demo path."""

from __future__ import annotations

import asyncio
from pathlib import Path
import sys
from time import perf_counter
from typing import Any

from demo.backend.schemas import DemoPatientCase, ToolExecution


class MCPToolError(RuntimeError):
    """Raised when the MCP server or protocol returns an unusable result."""


async def _run(case: DemoPatientCase, names: list[str]) -> list[ToolExecution]:
    from mcp import Client, StdioServerParameters

    root = Path(__file__).parents[2]
    env = {"PYTHONPATH": str(root)}
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "demo.mcp_server.server"],
        cwd=str(root),
        env=env,
    )
    rows: list[ToolExecution] = []
    async with Client(parameters) as client:
        listed = await client.list_tools()
        available = {tool.name for tool in listed.tools}
        missing = set(names) - available
        if missing:
            raise MCPToolError(f"MCP server omitted required tools: {sorted(missing)}")
        for name in names:
            started = perf_counter()
            result = await client.call_tool(name, {"case_id": case.case_id})
            if result.is_error or result.structured_content is None:
                raise MCPToolError(f"MCP tool {name} failed: {result.content}")
            envelope = dict(result.structured_content)
            if envelope.get("server") != "aether-clinical-tools" or envelope.get("transport") != "stdio":
                raise MCPToolError(f"invalid MCP provenance from {name}: {envelope}")
            rows.append(
                ToolExecution(
                    tool_name=name,
                    request={"case_id": case.case_id, "dataset_origin": case.dataset_origin},
                    response=dict(envelope["response"]),
                    execution_status="COMPLETE",
                    elapsed_ms=(perf_counter() - started) * 1000,
                    provenance="REAL MCP STDIO / SYNTHETIC DEMO FIXTURE",
                )
            )
    return rows


def run_all_mcp_tools(case: DemoPatientCase) -> list[ToolExecution]:
    """Execute all case tools over one real MCP stdio session."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(_run(case, case.available_tools))
    raise MCPToolError("synchronous MCP client cannot run inside an active asyncio event loop")
