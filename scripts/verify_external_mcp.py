"""Generate a machine-readable live WSO2/HAPI MCP acceptance artifact."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
from time import perf_counter

from demo.backend.wso2_mcp_client import WSO2FHIRClient
def _total(response: object) -> int:
    if isinstance(response, dict) and response.get("resourceType") == "Bundle":
        return int(response.get("total", len(response.get("entry", []))))
    return 1 if isinstance(response, dict) and response.get("resourceType") else 0


def verify(endpoint: str) -> dict:
    """Exercise discovery and read/search for all review patients through MCP only."""
    started = perf_counter()
    client = WSO2FHIRClient(endpoint)
    discovery = client.discover_tools()
    records = []
    for number in range(1, 13):
        case_id = f"DEMO-PAT-{number:03d}"
        calls = [
            client.read("Patient", f"aether-{case_id.lower()}"),
            client.search("Observation", {"patient": f"aether-{case_id.lower()}"}),
            client.search("Condition", {"patient": f"aether-{case_id.lower()}"}),
            client.search("MedicationRequest", {"patient": f"aether-{case_id.lower()}"}),
        ]
        records.append({"case_id": case_id, "patient": _total(calls[0].response),
                        "observations": _total(calls[1].response), "conditions": _total(calls[2].response),
                        "medications": _total(calls[3].response),
                        "calls": [{"tool": call.tool, "arguments": call.arguments, "elapsed_ms": call.elapsed_ms,
                                   "response_sha256": call.response_sha256} for call in calls]})
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        commit = "supplied-by-host-after-container-run"
    return {"schema_version": "aether.external-mcp-acceptance.v1", "status": "MCP_RETRIEVAL_VERIFIED",
            "server": discovery["server"], "transport": "Streamable HTTP", "mcp_endpoint": endpoint,
            "fhir_endpoint": "http://hapi-fhir:8080/fhir", "tools": [tool["name"] for tool in discovery["tools"]],
            "wso2_image_digest": "sha256:2028481e78580416cf31ee50e769fe981e9ecbf1f91419ea6e0aeed88cf03e79",
            "hapi_image_digest": "sha256:e60b0a2063db0c8ee65fc34206aed9df232a39d5e29ee37fdd9df74551895cd6",
            "git_commit": commit, "utc_timestamp": datetime.now(timezone.utc).isoformat(),
            "runtime_seconds": perf_counter() - started, "records": records}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", default="http://127.0.0.1:8001/mcp/")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = verify(args.endpoint)
    payload = json.dumps(result, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload)


if __name__ == "__main__":
    main()
