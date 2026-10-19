"""FastAPI localhost application for the removable review demo."""

from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import asdict
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Literal

from demo.backend.evidence import evidence_cards, system_status
from demo.backend.model_runtime import model_status, preload_model
from demo.backend.repository import get_case, load_cases
from demo.backend.service import get_live_replay, get_replay, get_run, run_induction, run_pipeline, run_rescue
from demo.backend.tools import run_all_tools, run_tool


class CaseRequest(BaseModel):
    """Request identifying exactly one isolated demo fixture."""
    case_id: str
    tool_name: str | None = None
    execution_mode: Literal["real_fhir_mcp_deterministic", "real_fhir_mcp_qwen", "mock_deterministic", "deterministic", "live_model_mcp"] = "real_fhir_mcp_deterministic"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Preload the pinned model before accepting live-mode review traffic."""
    if os.environ.get("AETHER_DEMO_MODE") == "live_model_mcp":
        preload_model()
    yield


app = FastAPI(title="AETHER Intermediate Review Demo", version="2.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_methods=["*"], allow_headers=["*"])


def _case(case_id: str):
    try:
        return get_case(case_id)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc


@app.get("/api/demo/health")
def health() -> dict:
    return {"status":"ok","bind_policy":"localhost_only","case_count":len(load_cases()),"model_loaded":model_status()["ready"]}


@app.get("/api/demo/cases")
def cases() -> list[dict]:
    return [case.to_dict() for case in load_cases()]


@app.get("/api/demo/cases/{case_id}")
def case_detail(case_id: str) -> dict:
    return _case(case_id).to_dict()


@app.get("/api/demo/mcp/tools")
def discover_mcp_tools():
    """Perform live MCP initialization and tool discovery; never return a hard-coded list."""
    try:
        from demo.backend.wso2_mcp_client import WSO2FHIRClient
        return WSO2FHIRClient().discover_tools()
    except (RuntimeError, OSError, ValueError, ImportError) as exc:
        raise HTTPException(503, f"external WSO2 MCP discovery failed: {exc}") from exc


@app.get("/api/demo/fhir/{case_id}")
def fhir_case(case_id: str):
    _case(case_id)
    try:
        from demo.backend.fhir_service import fetch_case
        return fetch_case(case_id)
    except (RuntimeError, OSError, ValueError, ImportError) as exc:
        raise HTTPException(503, f"external WSO2 MCP retrieval failed: {exc}") from exc


@app.post("/api/demo/tools/run")
def tools_run(request: CaseRequest):
    case = _case(request.case_id)
    if request.execution_mode == "real_fhir_mcp_deterministic":
        try:
            from demo.backend.fhir_service import fetch_case
            return fetch_case(request.case_id)
        except (RuntimeError, OSError, ValueError, ImportError) as exc:
            raise HTTPException(503, f"external WSO2 MCP retrieval failed: {exc}") from exc
    if request.execution_mode == "live_model_mcp":
        if request.tool_name:
            raise HTTPException(400, "live MCP mode runs the case tool set in one session")
        try:
            from demo.backend.mcp_client import run_all_mcp_tools
            return [asdict(item) for item in run_all_mcp_tools(case)]
        except (RuntimeError, OSError, ValueError, ImportError) as exc:
            raise HTTPException(503, f"real MCP execution failed: {exc}") from exc
    return asdict(run_tool(case, request.tool_name)) if request.tool_name else [asdict(item) for item in run_all_tools(case)]


def _execute(request: CaseRequest, action: str):
    if request.execution_mode == "real_fhir_mcp_deterministic":
        try:
            from demo.backend.fhir_service import run_fhir_pipeline, run_fhir_rescue
            if action == "clean": return run_fhir_pipeline(request.case_id, False)
            if action == "attack": return run_fhir_pipeline(request.case_id, True)
            if action == "rescue": return run_fhir_rescue(request.case_id)
            raise ValueError("induction is not exposed in primary FHIR mode")
        except (RuntimeError, OSError, ValueError, ImportError) as exc:
            raise HTTPException(503, f"external WSO2 MCP pipeline failed: {exc}") from exc
    if request.execution_mode in ("deterministic", "mock_deterministic"):
        return {
            "clean": lambda: run_pipeline(request.case_id, False),
            "attack": lambda: run_pipeline(request.case_id, True),
            "rescue": lambda: run_rescue(request.case_id),
            "induction": lambda: run_induction(request.case_id),
        }[action]()
    if request.execution_mode == "real_fhir_mcp_qwen":
        raise HTTPException(503, "optional Qwen-over-FHIR mode is not qualified")
    try:
        from demo.backend.live_service import run_live_induction, run_live_pipeline, run_live_rescue
        return {
            "clean": lambda: run_live_pipeline(request.case_id, False),
            "attack": lambda: run_live_pipeline(request.case_id, True),
            "rescue": lambda: run_live_rescue(request.case_id),
            "induction": lambda: run_live_induction(request.case_id),
        }[action]()
    except (RuntimeError, OSError, ValueError, ImportError) as exc:
        raise HTTPException(503, f"live model + MCP execution failed: {exc}") from exc


@app.post("/api/demo/pipeline/clean")
def pipeline_clean(request: CaseRequest): return _execute(request, "clean")


@app.post("/api/demo/pipeline/attack")
def pipeline_attack(request: CaseRequest): return _execute(request, "attack")


@app.post("/api/demo/pipeline/rescue")
def pipeline_rescue(request: CaseRequest): return _execute(request, "rescue")


@app.post("/api/demo/pipeline/induction")
def pipeline_induction(request: CaseRequest): return _execute(request, "induction")


@app.get("/api/demo/runs/{run_id}")
def runs(run_id: str):
    try: return get_run(run_id)
    except KeyError as exc: raise HTTPException(404, f"unknown run: {run_id}") from exc


@app.get("/api/demo/evidence")
def evidence(): return evidence_cards()


@app.get("/api/demo/system-status")
def status(): return system_status()


@app.get("/api/demo/model/status")
def local_model_status(): return model_status()


@app.post("/api/demo/model/preload")
def local_model_preload():
    try: return preload_model()
    except RuntimeError as exc: raise HTTPException(503, f"local-only model preload failed: {exc}") from exc


@app.get("/api/demo/replay/{case_id}")
def replay(case_id: str):
    _case(case_id)
    try: return get_replay(case_id)
    except KeyError as exc: raise HTTPException(404, f"no verified replay for {case_id}") from exc


@app.get("/api/demo/replay-live/{case_id}")
def live_replay(case_id: str):
    _case(case_id)
    try: return get_live_replay(case_id)
    except KeyError as exc: raise HTTPException(404, str(exc)) from exc


frontend = Path(__file__).parents[1] / "frontend" / "dist"
if frontend.is_dir():
    app.mount("/", StaticFiles(directory=frontend, html=True), name="frontend")
