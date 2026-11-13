"""Fail-closed, network-free verification of the packaged review demo."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fastapi.testclient import TestClient

from demo.backend.app import app


ROOT = Path(__file__).resolve().parents[1]


def verify(root: Path = ROOT, *, require_frontend_build: bool = True) -> dict[str, object]:
    """Verify static build, API contracts, fixtures and evidence status locally."""
    root = root.resolve()
    dist = root / "demo/frontend/dist"
    if require_frontend_build:
        if not (dist / "index.html").is_file() or not any((dist / "assets").glob("*.js")):
            raise FileNotFoundError("frontend production build is absent; run npm.cmd run build")
    client = TestClient(app)
    health = client.get("/api/demo/health")
    cases = client.get("/api/demo/cases")
    phase1 = client.get("/api/demo/phase1-status")
    if health.status_code != 200 or health.json().get("case_count") != 12:
        raise RuntimeError("demo health contract failed")
    if cases.status_code != 200 or len(cases.json()) != 12:
        raise RuntimeError("demo case contract failed")
    if phase1.status_code != 200 or len(phase1.json().get("stages", [])) != 22:
        raise RuntimeError("demo Phase-1 evidence contract failed")
    clean = client.post("/api/demo/pipeline/clean", json={"case_id": "DEMO-PAT-001", "execution_mode": "mock_deterministic"})
    attacked = client.post("/api/demo/pipeline/attack", json={"case_id": "DEMO-PAT-001", "execution_mode": "mock_deterministic"})
    if clean.status_code != 200 or attacked.status_code != 200:
        raise RuntimeError("deterministic review pipeline failed")
    if clean.json()["receiver"]["decision"] == attacked.json()["receiver"]["decision"]:
        raise RuntimeError("demo attack does not change the declared primary case decision")
    return {
        "overall": "PASS", "case_count": 12, "phase1_gate_count": 22,
        "frontend_build_verified": require_frontend_build,
        "live_external_services_tested": False,
        "claim_boundary": "Network-free packaging verification; not live MCP or model evidence.",
    }


def main() -> None:
    """Print the package verification result."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--allow-missing-frontend-build", action="store_true")
    arguments = parser.parse_args()
    print(json.dumps(verify(arguments.root, require_frontend_build=not arguments.allow_missing_frontend_build), indent=2))


if __name__ == "__main__":
    main()
