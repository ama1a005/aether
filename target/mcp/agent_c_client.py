"""Strict MCP client used by the approved real-Qwen Agent C runner."""

from __future__ import annotations

import asyncio
from contextlib import AsyncExitStack
from datetime import timedelta
from pathlib import Path
import sys
from typing import Any


async def _call(registry: Path, case_id: str) -> dict[str, Any]:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    root = Path(__file__).resolve().parents[2]
    parameters = StdioServerParameters(
        command=sys.executable, args=["-m", "target.mcp.agent_c_server"], cwd=str(root),
        env={"PYTHONPATH": str(root), "AETHER_AGENT_C_REGISTRY": str(registry.resolve())},
    )
    async with AsyncExitStack() as stack:
        read, write = await stack.enter_async_context(stdio_client(parameters))
        client = await stack.enter_async_context(ClientSession(
            read, write, read_timeout_seconds=timedelta(seconds=20)))
        await client.initialize()
        listed = await client.list_tools()
        tools = [{"name": item.name, "description": item.description,
                  "inputSchema": item.inputSchema} for item in listed.tools]
        if [item["name"] for item in tools].count("get_vital_signs") != 1:
            raise RuntimeError("MCP discovery did not expose exactly one get_vital_signs tool")
        result = await client.call_tool("get_vital_signs", {"case_id": case_id})
        if result.isError or result.structuredContent is None:
            raise RuntimeError(f"MCP get_vital_signs failed: {result.content}")
        envelope = dict(result.structuredContent)
        if (envelope.get("server") != "aether-agent-c-vitals"
                or envelope.get("transport") != "stdio"
                or envelope.get("tool_name") != "get_vital_signs"):
            raise ValueError("MCP tool returned invalid provenance")
        response = envelope.get("response")
        if not isinstance(response, dict) or response.get("case_id") != case_id:
            raise ValueError("MCP tool returned a mismatched response")
        forbidden = {"ground_truth_decision", "split", "dataset_version"}
        if forbidden.intersection(response):
            raise ValueError("MCP response leaked a forbidden field")
        return {"discovered_tools": tools, "request": {"case_id": case_id},
                "envelope": envelope, "response": response}


def call_vital_signs(registry: Path, case_id: str) -> dict[str, Any]:
    """Discover and call the real stdio tool from synchronous experiment code."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(_call(registry, case_id))
    raise RuntimeError("Agent C MCP client cannot run inside an active event loop")
