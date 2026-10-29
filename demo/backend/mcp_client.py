"""Real MCP stdio client used by the live AETHER demo path."""

from __future__ import annotations

import asyncio
from contextlib import AsyncExitStack
from datetime import timedelta
from pathlib import Path
import sys
from time import perf_counter
from typing import Any

from demo.backend.schemas import DemoPatientCase, ToolExecution


class MCPToolError(RuntimeError):
    """Raised when the MCP server or protocol returns an unusable result."""


async def _run(case: DemoPatientCase, names: list[str]) -> list[ToolExecution]:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    root = Path(__file__).parents[2]
    env = {"PYTHONPATH": str(root)}
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "demo.mcp_server.server"],
        cwd=str(root),
        env=env,
    )
    rows: list[ToolExecution] = []
    async with AsyncExitStack() as stack:
        read, write = await stack.enter_async_context(stdio_client(parameters))
        client = await stack.enter_async_context(ClientSession(read, write, read_timeout_seconds=timedelta(seconds=15)))
        await client.initialize()
        listed = await client.list_tools()
        available = {tool.name for tool in listed.tools}
        missing = set(names) - available
        if missing:
            raise MCPToolError(f"MCP server omitted required tools: {sorted(missing)}")
        for name in names:
            started = perf_counter()
            result = await client.call_tool(name, {"case_id": case.case_id})
            if result.isError or result.structuredContent is None:
                raise MCPToolError(f"MCP tool {name} failed: {result.content}")
            envelope = dict(result.structuredContent)
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


async def _discover() -> list[dict[str, Any]]:
    """Discover real stdio MCP tools and retain their advertised schemas."""
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    root = Path(__file__).parents[2]
    parameters = StdioServerParameters(command=sys.executable,
        args=["-m", "demo.mcp_server.server"], cwd=str(root), env={"PYTHONPATH": str(root)})
    async with AsyncExitStack() as stack:
        read, write = await stack.enter_async_context(stdio_client(parameters))
        client = await stack.enter_async_context(ClientSession(
            read, write, read_timeout_seconds=timedelta(seconds=15)))
        await client.initialize()
        result = await client.list_tools()
        return [{"name": tool.name, "description": tool.description,
                 "inputSchema": tool.inputSchema} for tool in result.tools]


def run_all_mcp_tools(case: DemoPatientCase) -> list[ToolExecution]:
    """Execute all case tools over one real MCP stdio session."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(_run(case, case.available_tools))
    raise MCPToolError("synchronous MCP client cannot run inside an active asyncio event loop")


def discover_mcp_tools() -> list[dict[str, Any]]:
    """Synchronously inspect the real MCP server from non-async experiment code."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(_discover())
    raise MCPToolError("synchronous MCP discovery cannot run inside an active asyncio event loop")


def run_selected_mcp_tools(case: DemoPatientCase, names: list[str]) -> list[ToolExecution]:
    """Execute selected tools over real MCP stdio with normal provenance checks."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(_run(case, names))
    raise MCPToolError("synchronous MCP client cannot run inside an active asyncio event loop")
