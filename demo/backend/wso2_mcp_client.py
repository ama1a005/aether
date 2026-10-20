"""Official-SDK Streamable HTTP client for the external WSO2 FHIR MCP server."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from hashlib import sha256
import json
import os
from time import perf_counter
from typing import Any


class ExternalMCPError(RuntimeError):
    """Raised when the required external MCP path is unavailable or invalid."""


@dataclass(frozen=True)
class MCPCallRecord:
    tool: str
    arguments: dict[str, Any]
    response: Any
    elapsed_ms: float
    response_sha256: str
    server: dict[str, Any]
    transport: str = "Streamable HTTP"


def _decode(result: Any) -> Any:
    if getattr(result, "isError", False):
        raise ExternalMCPError(f"WSO2 MCP tool failed: {result.content}")
    structured = getattr(result, "structuredContent", None)
    if structured is not None:
        return structured
    texts = [item.text for item in result.content if hasattr(item, "text")]
    if not texts:
        raise ExternalMCPError("WSO2 MCP returned no JSON/text content")
    try:
        return json.loads("".join(texts))
    except json.JSONDecodeError as exc:
        raise ExternalMCPError("WSO2 MCP returned non-JSON FHIR content") from exc


class WSO2FHIRClient:
    """Short-lived, fail-closed client for generic WSO2 FHIR MCP operations."""

    def __init__(self, endpoint: str | None = None) -> None:
        self.endpoint = endpoint or os.getenv("AETHER_FHIR_MCP_ENDPOINT", "http://127.0.0.1:8001/mcp/")

    async def _session(self, operation: str, payload: dict[str, Any] | None = None) -> Any:
        try:
            from mcp import ClientSession
            try:
                from mcp.client.streamable_http import streamable_http_client as open_streamable_http
            except ImportError:  # Compatibility with the older SDK bundled by the pinned WSO2 image.
                from mcp.client.streamable_http import streamablehttp_client as open_streamable_http
            async with open_streamable_http(self.endpoint) as (read, write, _):
                async with ClientSession(read, write) as session:
                    initialized = await session.initialize()
                    server = initialized.serverInfo.model_dump(mode="json")
                    if operation == "list_tools":
                        tools = await session.list_tools()
                        return {"server": server, "tools": [tool.model_dump(mode="json") for tool in tools.tools]}
                    started = perf_counter()
                    result = await session.call_tool(operation, payload or {})
                    response = _decode(result)
                    encoded = json.dumps(response, sort_keys=True, default=str).encode()
                    return MCPCallRecord(operation, payload or {}, response, (perf_counter() - started) * 1000,
                                         sha256(encoded).hexdigest(), server)
        except ExternalMCPError:
            raise
        except Exception as exc:
            raise ExternalMCPError(f"external WSO2 MCP unavailable at {self.endpoint}: {exc}") from exc

    def _run(self, operation: str, payload: dict[str, Any] | None = None) -> Any:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self._session(operation, payload))
        raise ExternalMCPError("synchronous external MCP adapter cannot run inside an active event loop")

    def discover_tools(self) -> dict[str, Any]:
        """Initialize and return the server's live tool schemas."""
        return self._run("list_tools")

    def read(self, resource_type: str, resource_id: str) -> MCPCallRecord:
        """Read one FHIR resource through WSO2's generic read tool."""
        return self._run("read", {"type": resource_type, "id": resource_id})

    def search(self, resource_type: str, search_params: dict[str, str]) -> MCPCallRecord:
        """Search FHIR resources through WSO2's generic search tool."""
        return self._run("search", {"type": resource_type, "searchParam": search_params})

