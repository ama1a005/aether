"""Opt-in real stdio MCP protocol check for the isolated demo environment."""

from __future__ import annotations

import importlib.util

import pytest

from demo.backend.repository import get_case


@pytest.mark.skipif(importlib.util.find_spec("mcp") is None, reason="official MCP SDK not installed in research environment")
def test_real_mcp_stdio_lists_and_calls_tools() -> None:
    from demo.backend.mcp_client import run_all_mcp_tools

    case = get_case("DEMO-PAT-001")
    rows = run_all_mcp_tools(case)
    assert [row.tool_name for row in rows] == case.available_tools
    assert all(row.provenance == "REAL MCP STDIO / SYNTHETIC DEMO FIXTURE" for row in rows)
