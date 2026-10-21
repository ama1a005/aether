# External FHIR MCP Integration

## Pinned third-party components

- WSO2 repository: `https://github.com/wso2/fhir-mcp-server`; inspected main commit `2a915a48dcd173ccff782252dfac09351ff44f3f`.
- Package metadata: `fhir-mcp-server 0.10.0`, Apache-2.0, `mcp[cli]==1.27.1`.
- Image: `wso2/fhir-mcp-server@sha256:2028481e78580416cf31ee50e769fe981e9ecbf1f91419ea6e0aeed88cf03e79`.
- Runtime identity: `FHIR MCP Server 1.9.1`.
- HAPI: `hapiproject/hapi:v8.4.0-2@sha256:e60b0a2063db0c8ee65fc34206aed9df232a39d5e29ee37fdd9df74551895cd6`, Apache-2.0, FHIR R4.

The current WSO2 digest is ARM64-only. Docker Desktop can emulate it on this AMD64 workstation, but native AMD64 availability remains an upstream portability limitation.

## Review architecture

`React -> FastAPI -> official MCP Python client -> Streamable HTTP -> WSO2 FHIR MCP -> FHIR HTTP -> local HAPI FHIR R4`.

Compose is `demo/external_mcp/docker-compose.review.yml`. HAPI is `127.0.0.1:8080/fhir`; the canonical MCP URL is `127.0.0.1:8001/mcp/`. Authorization is disabled only for this localhost synthetic sandbox. Live discovery returned `get_capabilities`, `search`, `read`, `create`, `update`, `delete`, and `get_user`.

`scripts/seed_review_fhir.py` is the only direct-FHIR setup path. Stable PUT ids make it idempotent. Interactive retrieval is fail-closed through WSO2. All records are synthetic and tagged `https://aether.invalid/fhir/tags|synthetic-review`.

## Current limitation

As of 2026-10-21, the host has `mcp==1.27.1` installed. The remaining failure is
host-to-container HTTP framing: native curl and Python received
`Transfer-Encoding: chunked` followed by an unframed JSON body. The same
initialization inside the WSO2 container returned valid `Content-Length: 383` and
JSON. Restarting only WSO2 did not clear the failure. The precise interfering
component is not yet established; do not attribute it to RAM or ARM emulation.
Host FastAPI external-MCP acceptance remains blocked. No direct-FHIR or mock
fallback is enabled in real mode.

Correction: the inspected upstream-main dependency declaration is not the
installed SDK version in the pinned image. That image reports server version
1.9.1 and exposes the older SDK transport entry point.

Optional proof: run MCP Inspector with Streamable HTTP URL `http://127.0.0.1:8001/mcp/`.

