"""Opt-in real stdio MCP protocol check for the isolated demo environment."""

from __future__ import annotations

import importlib.util
import asyncio
from pathlib import Path
import sys

import pytest

@pytest.mark.skipif(importlib.util.find_spec("mcp") is None, reason="official MCP SDK not installed in research environment")
def test_real_mcp_stdio_lists_and_calls_tools() -> None:
    from mcp import Client, StdioServerParameters

    async def exercise() -> None:
        root = Path(__file__).parents[2]
        parameters = StdioServerParameters(
            command=sys.executable,
            args=["-m", "demo.mcp_server.server"],
            cwd=str(root),
            env={"PYTHONPATH": str(root)},
        )
        client = Client(parameters)
        async with client:
            assert client.protocol_version is not None
            tools = await client.list_tools()
            assert {tool.name for tool in tools.tools} == {
                "patient_record", "ecg_analysis", "lab_results", "vitals_monitor",
                "medication_safety", "allergy_check", "neuro_assessment", "risk_assessment",
            }
            for name in ("patient_record", "ecg_analysis", "lab_results"):
                result = await client.call_tool(name, {"case_id": "DEMO-PAT-001"})
                assert result.is_error is False
                assert result.structured_content["server"] == "aether-clinical-tools"
                assert result.structured_content["tool_name"] == name
                assert result.structured_content["case_id"] == "DEMO-PAT-001"
        with pytest.raises(RuntimeError):
            await client.call_tool("patient_record", {"case_id": "DEMO-PAT-001"})

    asyncio.run(exercise())
