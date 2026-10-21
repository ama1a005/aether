"""Opt-in real stdio MCP protocol check for the isolated demo environment."""

from __future__ import annotations

import importlib.util
import asyncio
from contextlib import AsyncExitStack
from pathlib import Path
import sys

import pytest

@pytest.mark.skipif(importlib.util.find_spec("mcp") is None, reason="official MCP SDK not installed in research environment")
def test_real_mcp_stdio_lists_and_calls_tools() -> None:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    async def exercise() -> None:
        root = Path(__file__).parents[2]
        parameters = StdioServerParameters(
            command=sys.executable,
            args=["-m", "demo.mcp_server.server"],
            cwd=str(root),
            env={"PYTHONPATH": str(root)},
        )
        async with AsyncExitStack() as stack:
            read, write = await stack.enter_async_context(stdio_client(parameters))
            client = await stack.enter_async_context(ClientSession(read, write))
            initialized = await client.initialize()
            assert initialized.protocolVersion is not None
            tools = await client.list_tools()
            assert {tool.name for tool in tools.tools} == {
                "patient_record", "ecg_analysis", "lab_results", "vitals_monitor",
                "medication_safety", "allergy_check", "neuro_assessment", "risk_assessment",
            }
            for name in ("patient_record", "ecg_analysis", "lab_results"):
                result = await client.call_tool(name, {"case_id": "DEMO-PAT-001"})
                assert result.isError is False
                assert result.structuredContent["server"] == "aether-clinical-tools"
                assert result.structuredContent["tool_name"] == name
                assert result.structuredContent["case_id"] == "DEMO-PAT-001"

    asyncio.run(exercise())
