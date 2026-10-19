"""FastAPI localhost application for the removable review demo."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from demo.backend.evidence import evidence_cards, system_status
from demo.backend.model_runtime import model_status, preload_model
from demo.backend.repository import get_case, load_cases
from demo.backend.service import get_replay, get_run, run_induction, run_pipeline, run_rescue
from demo.backend.tools import run_all_tools, run_tool


class CaseRequest(BaseModel):
    """Request identifying exactly one isolated demo fixture."""
    case_id: str
    tool_name: str | None = None


app = FastAPI(title="AETHER Intermediate Review Demo", version="1.0.0")
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


@app.post("/api/demo/tools/run")
def tools_run(request: CaseRequest):
    case = _case(request.case_id)
    return asdict(run_tool(case, request.tool_name)) if request.tool_name else [asdict(item) for item in run_all_tools(case)]


@app.post("/api/demo/pipeline/clean")
def pipeline_clean(request: CaseRequest): return run_pipeline(request.case_id, False)


@app.post("/api/demo/pipeline/attack")
def pipeline_attack(request: CaseRequest): return run_pipeline(request.case_id, True)


@app.post("/api/demo/pipeline/rescue")
def pipeline_rescue(request: CaseRequest): return run_rescue(request.case_id)


@app.post("/api/demo/pipeline/induction")
def pipeline_induction(request: CaseRequest): return run_induction(request.case_id)


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


frontend = Path(__file__).parents[1] / "frontend" / "dist"
if frontend.is_dir():
    app.mount("/", StaticFiles(directory=frontend, html=True), name="frontend")
