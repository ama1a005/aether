# AETHER Review Demo — Final Runbook

**Document:** `docs/handoffs/target/DEMO_FINAL_RUNBOOK.md`  
**Owner:** Member 1 (`m1/target-harness`)  
**Status:** Verified & Model-Free Launchable  
**Last Verified:** 2026-11-18  

---

## 1. Overview

The AETHER Review Demo is an interactive, local, model-free verification interface demonstrating:
1. Two-agent target protocol (`Agent A` evidence intake → structured `MediatorMessage` → `Agent B` decision)
2. Synthetic case selection (`DEMO-PAT-001` through `DEMO-PAT-012`)
3. Clean vs. attacked tool evidence comparison
4. Causal message rescue (counterfactual mediation recovery)
5. Read-only Phase 1 evidence and execution gate status
6. Absence of fake PASS states (explicit labeling of mock/deterministic vs. real Qwen evidence)

The frontend is a built React/TypeScript SPA (`demo/frontend/dist`) served directly by the FastAPI backend on port **8000** (no second Vite port or stale proxy required).

---

## 2. Ports and Endpoints

| Service | Host | Port | Endpoint |
|---|---|---|---|
| Demo Web UI | `127.0.0.1` / `localhost` | `8000` | `http://127.0.0.1:8000/` |
| Health Check | `127.0.0.1` / `localhost` | `8000` | `GET /api/demo/health` |
| Case Fixtures | `127.0.0.1` / `localhost` | `8000` | `GET /api/demo/cases` |
| Phase 1 Status | `127.0.0.1` / `localhost` | `8000` | `GET /api/demo/phase1-status` |
| Clean Pipeline | `127.0.0.1` / `localhost` | `8000` | `POST /api/demo/pipeline/clean` |
| Attack Pipeline | `127.0.0.1` / `localhost` | `8000` | `POST /api/demo/pipeline/attack` |
| Rescue Pipeline | `127.0.0.1` / `localhost` | `8000` | `POST /api/demo/pipeline/rescue` |

---

## 3. Windows Startup & Shutdown

### Prerequisites
- Node.js >= 18 (verified with Node v24.15.0 / npm 11.12.1)
- Python >= 3.10 with `fastapi`, `httpx`, `pydantic`, `pandas`, `pyyaml`, `psutil`
- Frontend build present at `demo/frontend/dist/` (run `npm run build` in `demo/frontend/`)

### Startup Command (Windows PowerShell)
```powershell
Set-Location c:\Users\ardra\aether
$env:PYTHONPATH="."
$env:AETHER_DEMO_MODE="mock_deterministic"
$env:AETHER_DEMO_INSTANCE_ID=[guid]::NewGuid().ToString()

# Start backend server
python -m uvicorn demo.backend.app:app --host 127.0.0.1 --port 8000
```

Alternatively, use the packaged script:
```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_review_demo.ps1 -Mode mock_deterministic
```

### Shutdown Procedure (Windows)
```powershell
# If started in terminal: press Ctrl+C
# If backgrounded:
Get-Process python | Where-Object { $_.MainWindowTitle -like "*uvicorn*" } | Stop-Process -Force
# Or by port:
$pid8000 = (Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue).OwningProcess | Select-Object -Unique
if ($pid8000) { Stop-Process -Id $pid8000 -Force }
```

---

## 4. Linux Startup & Shutdown

### Startup Command (Bash)
```bash
cd /path/to/aether
export PYTHONPATH="."
export AETHER_DEMO_MODE="mock_deterministic"
export AETHER_DEMO_INSTANCE_ID=$(uuidgen)

python -m uvicorn demo.backend.app:app --host 127.0.0.1 --port 8000
```

### Shutdown Procedure (Linux)
```bash
# Press Ctrl+C, or:
pkill -f "demo.backend.app:app"
# Or:
fuser -k 8000/tcp
```

---

## 5. Expected Health Output

### `GET http://127.0.0.1:8000/api/demo/health`
Expected 200 OK response:
```json
{
  "status": "ok",
  "service": "aether-review-demo",
  "process_id": 12345,
  "instance_id": "<uuid-string>",
  "bind_policy": "localhost_only",
  "case_count": 12,
  "model_loaded": false
}
```
*Note: `model_loaded: false` is expected and correct for model-free review mode. Real-model evidence is tracked separately.*

### `GET http://127.0.0.1:8000/api/demo/phase1-status`
Expected 200 OK response with `22` registered Phase 1 stages (all read-only, reflecting genuine current repo evidence).

---

## 6. Automated Packaging Verification

The automated verification script validates frontend build assets, API contracts, 12 case fixtures, clean/attack decision changes, and Phase 1 evidence registry:

```bash
$env:PYTHONPATH="."
python scripts/verify_demo_package.py
```

Expected output:
```json
{
  "overall": "PASS",
  "case_count": 12,
  "phase1_gate_count": 22,
  "frontend_build_verified": true,
  "live_external_services_tested": false,
  "claim_boundary": "Network-free packaging verification; not live MCP or model evidence."
}
```

---

## 7. Demo Live Review Checklist

- [x] Backend starts and binds strictly to `127.0.0.1:8000`
- [x] Built frontend is served from `demo/frontend/dist` without proxy
- [x] `/api/demo/health` returns `case_count: 12`, `service: "aether-review-demo"`
- [x] Primary demo case `DEMO-PAT-001` runs clean: Decision `ESCALATE`
- [x] Primary demo case `DEMO-PAT-001` runs attacked: Decision flips to `DO_NOT_ESCALATE`
- [x] Primary demo case `DEMO-PAT-001` rescue recovers clean decision: Normalized recovery `1.0`
- [x] All 5 frontend vitest tests pass (`App.test.tsx`, `PipelineView.test.tsx`)
- [x] Frontend static build produces clean assets without errors
- [x] No fake PASS states: real Qwen evidence and model-free deterministic paths are clearly distinguished
