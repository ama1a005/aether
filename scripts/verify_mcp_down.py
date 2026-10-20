"""Verify that real MCP mode fails closed when WSO2 is unavailable."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from demo.backend.wso2_mcp_client import ExternalMCPError, WSO2FHIRClient


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        WSO2FHIRClient(args.endpoint).discover_tools()
    except ExternalMCPError as exc:
        result = {"status": "PASS", "dependency": "WSO2 FHIR MCP", "failed_closed": True,
                  "direct_fhir_fallback": False, "mock_fallback": False, "fixture_fallback": False,
                  "error": str(exc)}
        args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result))
        return
    raise RuntimeError("MCP request unexpectedly succeeded while WSO2 was stopped")


if __name__ == "__main__":
    main()
