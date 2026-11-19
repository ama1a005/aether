"""MCP stdio server for the approved real-Qwen Agent C experiment."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

try:
    from mcp.server.mcpserver import MCPServer as FastMCP
except ImportError:
    from mcp.server.fastmcp import FastMCP

from target.mcp.tools import get_vital_signs as compute_vital_signs


SERVER_NAME = "aether-agent-c-vitals"
mcp = FastMCP(SERVER_NAME, instructions="Read-only frozen development vital-sign evidence.")


def _registry() -> dict[str, dict[str, Any]]:
    """Load the explicitly supplied frozen registry without a default path."""
    configured = os.environ.get("AETHER_AGENT_C_REGISTRY")
    if not configured:
        raise RuntimeError("AETHER_AGENT_C_REGISTRY is required")
    path = Path(configured).resolve()
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = payload.get("cases") if isinstance(payload, dict) else None
    if not isinstance(cases, list):
        raise ValueError("Agent C registry lacks a cases list")
    result: dict[str, dict[str, Any]] = {}
    for case in cases:
        if not isinstance(case, dict) or not isinstance(case.get("case_id"), str):
            raise ValueError("Agent C registry contains a malformed case")
        if case.get("split") != "development":
            continue
        result[case["case_id"]] = case
    return result


@mcp.tool(name="get_vital_signs")
def get_vital_signs(case_id: str) -> dict[str, Any]:
    """Return feature-derived vital signs without labels or split metadata."""
    case = _registry().get(case_id)
    if case is None:
        raise ValueError(f"unknown approved development case: {case_id}")
    result = compute_vital_signs(case_id, dict(case.get("features", {})))
    return {"server": SERVER_NAME, "transport": "stdio", "tool_name": "get_vital_signs",
            "response": {"case_id": case_id, **result}}


def main() -> None:
    """Serve the frozen tool over MCP stdio."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
