"""Real MCP plus real local-Qwen execution path for the review demo."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
import platform
import subprocess
import sys
from time import perf_counter
from typing import Any
from uuid import uuid4

import torch

from demo.backend.config import MODEL_ID, MODEL_REVISION
from demo.backend.mcp_client import run_all_mcp_tools
from demo.backend.model_runtime import run_receiver, run_sender
from demo.backend.repository import get_case
from demo.backend.service import _attack_tools, _save_run
from paired_trace.metrics import LABEL_TO_DECISION, mediation_recovery
from paired_trace.schemas import MediatorMessage, canonical_json


def _commit() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()


def _environment_hash() -> str:
    freeze = subprocess.run(
        [sys.executable, "-m", "pip", "freeze", "--local"], check=True, capture_output=True, text=True
    ).stdout
    return sha256(freeze.encode("utf-8")).hexdigest()


def run_live_pipeline(case_id: str, attacked: bool = False) -> dict[str, Any]:
    """Execute real MCP tools, Agent A generation, and Agent B logit scoring."""
    started = perf_counter()
    case = get_case(case_id)
    tool_rows = [asdict(row) for row in run_all_mcp_tools(case)]
    attack_delta = None
    if attacked:
        tool_rows, attack_delta = _attack_tools(tool_rows, case.primary_attack_target)
    sender = run_sender(tool_rows)
    mediator = MediatorMessage.from_sender_code(
        case.case_id,
        sender["parsed"]["decision_code"],
        str(sender["parsed"].get("rationale", "")),
    )
    mediator_dict = asdict(mediator)
    receiver = run_receiver(mediator.serialize())
    decision = LABEL_TO_DECISION[receiver["decision_code"]]
    run_id = f"demo_live_{case.case_id.lower()}_{'attack' if attacked else 'clean'}_{uuid4().hex[:8]}"
    result = {
        "run_id": run_id,
        "case_id": case.case_id,
        "condition": "attacked" if attacked else "clean",
        "provenance_type": "LIVE MODEL + REAL MCP EXECUTION",
        "execution_mode": "live_model_mcp",
        "model": {"id": MODEL_ID, "revision": MODEL_REVISION, "used_for_this_run": True, "dtype": "float16", "device": "cuda"},
        "tools": tool_rows,
        "attack_delta": attack_delta,
        "sender": sender,
        "mediator": {"raw": mediator.serialize(), "parsed": mediator_dict, "sha256": mediator.sha256()},
        "receiver": {**receiver, "decision": decision, "received_mediator_sha256": mediator.sha256()},
        "expected_action": case.expected_action,
        "correct": decision == case.expected_action,
        "git_commit": _commit(),
        "uncommitted_diff": bool(subprocess.run(["git", "status", "--porcelain"], check=True, capture_output=True, text=True).stdout),
        "dataset_manifest_hashes": {"demo_cases": sha256(canonical_json(case.to_dict()).encode()).hexdigest()},
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "tokenizer_revision": MODEL_REVISION,
        "prompt_versions": {"agent_a": "demo-agent-a-v1", "agent_b": "demo-agent-b-v1"},
        "random_seeds": [0],
        "hardware": f"{torch.cuda.get_device_name(0)}; {platform.platform()}",
        "python_env_hash": _environment_hash(),
        "command_line": " ".join(sys.argv),
        "config_file": "demo/backend/config.py",
        "raw_output_path": f"demo/artifacts/runs/{run_id}.json",
        "runtime_seconds": perf_counter() - started,
        "utc_timestamp": datetime.now(timezone.utc).isoformat(),
        "validation_executions": 0,
        "test_executions": 0,
    }
    _save_run(result)
    return result


def run_live_rescue(case_id: str) -> dict[str, Any]:
    """Patch the clean real-model mediator into the attacked Agent B context."""
    clean = run_live_pipeline(case_id, False)
    attacked = run_live_pipeline(case_id, True)
    rescued_receiver = run_receiver(clean["mediator"]["raw"])
    score_after = rescued_receiver["score"]
    result = {
        "run_id": f"demo_live_{case_id.lower()}_rescue_{uuid4().hex[:8]}",
        "case_id": case_id,
        "provenance_type": "LIVE MODEL + REAL MCP EXECUTION",
        "execution_mode": "live_model_mcp",
        "intervention": "whole_clean_message_substitution",
        "attacked_outcome": attacked["receiver"],
        "clean_mediator": clean["mediator"],
        "rescued_outcome": {**rescued_receiver, "decision": LABEL_TO_DECISION[rescued_receiver["decision_code"]]},
        "score_before": attacked["receiver"]["score"],
        "score_after": score_after,
        "normalized_recovery": mediation_recovery(clean["receiver"]["score"], attacked["receiver"]["score"], score_after),
        "git_commit": _commit(),
        "utc_timestamp": datetime.now(timezone.utc).isoformat(),
    }
    _save_run(result)
    return result


def run_live_induction(case_id: str) -> dict[str, Any]:
    """Supply the attacked real-model mediator to a fresh Agent B evaluation."""
    clean = run_live_pipeline(case_id, False)
    attacked = run_live_pipeline(case_id, True)
    induced = run_receiver(attacked["mediator"]["raw"])
    return {
        "case_id": case_id,
        "provenance_type": "LIVE MODEL + REAL MCP EXECUTION",
        "execution_mode": "live_model_mcp",
        "intervention": "attacked_message_induction",
        "clean_outcome": clean["receiver"],
        "induced_outcome": {**induced, "decision": LABEL_TO_DECISION[induced["decision_code"]]},
        "attacked_mediator": attacked["mediator"],
    }
