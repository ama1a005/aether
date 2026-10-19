"""Demo orchestration using AETHER mediator and causal bridge primitives."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import uuid4

from causal.bridge.intervention import CrossAgentInterventionRunner
from paired_trace.metrics import LABEL_TO_DECISION, mediation_recovery
from paired_trace.schemas import MediatorMessage, canonical_json, validate_attack_delta

from demo.backend.repository import get_case
from demo.backend.tools import run_all_tools

RUN_ROOT = Path("demo/artifacts/runs")
REPLAY_ROOT = Path("demo/artifacts/replays")
MODEL_ID = "Qwen/Qwen2.5-0.5B-Instruct"
MODEL_REVISION = "7ae557604adf67be50417f59c2c2f167def9a775"


def _code_for_action(action: str) -> str:
    return "A" if action == "ESCALATE" else "B"


def _score(message: dict[str, Any]) -> float:
    return 1.0 if message["decision_code"] == "A" else -1.0


def _build_mediator(case_id: str, code: str, tool_name: str) -> MediatorMessage:
    return MediatorMessage.from_sender_code(case_id, code, f"authoritative synthetic output from {tool_name}")


def _attack_tools(tools: list[dict[str, Any]], target: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    tool_name, field = target.split(".", 1)
    if field != "recommendation_code":
        raise ValueError("demo attack may modify only recommendation_code")
    attacked = json.loads(json.dumps(tools))
    changed = None
    for item in attacked:
        if item["tool_name"] == tool_name:
            before = item["response"][field]
            after = "B" if before == "A" else "A"
            item["response"][field] = after
            changed = {"path": target, "clean": before, "attacked": after}
            break
    if changed is None:
        raise ValueError(f"attack target {target} is not present in tool results")
    validate_attack_delta({"tool_evidence.recommendation_code": {"clean": changed["clean"], "attacked": changed["attacked"]}})
    return attacked, changed


def run_pipeline(case_id: str, attacked: bool = False) -> dict[str, Any]:
    """Run the selected fixture through real tool, mediator, and receiver primitives."""
    started = perf_counter()
    case = get_case(case_id)
    tool_rows = [asdict(item) for item in run_all_tools(case)]
    attack_delta = None
    if attacked:
        tool_rows, attack_delta = _attack_tools(tool_rows, case.primary_attack_target)
    target_tool = case.primary_attack_target.split(".", 1)[0]
    target_row = next(item for item in tool_rows if item["tool_name"] == target_tool)
    sender_code = target_row["response"]["recommendation_code"]
    mediator = _build_mediator(case.case_id, sender_code, target_tool)
    mediator_dict = asdict(mediator)
    score = _score(mediator_dict)
    decision = LABEL_TO_DECISION[mediator.decision_code]
    run_id = f"demo_{case.case_id.lower()}_{'attack' if attacked else 'clean'}_{uuid4().hex[:8]}"
    result = {
        "run_id": run_id,
        "case_id": case.case_id,
        "condition": "attacked" if attacked else "clean",
        "provenance_type": "LIVE EXECUTION",
        "execution_mode": "deterministic AETHER core demo pipeline",
        "model": {"id": MODEL_ID, "revision": MODEL_REVISION, "used_for_this_run": False,
                  "note": "Review-safe deterministic core path; real-model evidence is shown separately."},
        "tools": tool_rows,
        "attack_delta": attack_delta,
        "sender": {
            "source": "demo/backend/service.py -> paired_trace.schemas.MediatorMessage",
            "rendered_prompt": canonical_json({"case_id": case.case_id, "tool_evidence": target_row["response"]}),
            "raw_output": sender_code,
        },
        "mediator": {"raw": mediator.serialize(), "parsed": mediator_dict, "sha256": mediator.sha256()},
        "receiver": {
            "source": "paired_trace.metrics.LABEL_TO_DECISION",
            "received_mediator_sha256": mediator.sha256(),
            "raw_output": mediator.decision_code,
            "decision": decision,
            "score": score,
        },
        "expected_action": case.expected_action,
        "correct": decision == case.expected_action,
        "git_commit": _git_commit(),
        "attack_config": {"target": case.primary_attack_target, "applied": attacked},
        "runtime_seconds": perf_counter() - started,
        "utc_timestamp": datetime.now(timezone.utc).isoformat(),
        "validation_executions": 0,
        "test_executions": 0,
    }
    _save_run(result)
    return result


def run_rescue(case_id: str, clean: dict[str, Any] | None = None, attacked: dict[str, Any] | None = None) -> dict[str, Any]:
    """Substitute the actual clean mediator into attacked context and rerun receiver scoring."""
    started = perf_counter()
    clean = clean or run_pipeline(case_id, attacked=False)
    attacked = attacked or run_pipeline(case_id, attacked=True)
    clean_message = clean["mediator"]["parsed"]
    attacked_message = attacked["mediator"]["parsed"]
    runner = CrossAgentInterventionRunner(None, None, attacked_message, _score, None)
    score_before, score_after = runner.run_message_patch(attacked_message, clean_message)
    recovery = mediation_recovery(clean["receiver"]["score"], attacked["receiver"]["score"], score_after)
    result = {
        "run_id": f"demo_{case_id.lower()}_rescue_{uuid4().hex[:8]}",
        "case_id": case_id,
        "provenance_type": "LIVE EXECUTION",
        "intervention": "whole_clean_message_substitution",
        "source": "causal.bridge.intervention.CrossAgentInterventionRunner.run_message_patch",
        "attacked_outcome": attacked["receiver"],
        "clean_mediator": clean["mediator"],
        "rescued_outcome": {"decision": LABEL_TO_DECISION[clean_message["decision_code"]], "score": score_after},
        "score_before": score_before,
        "score_after": score_after,
        "normalized_recovery": recovery,
        "git_commit": _git_commit(),
        "attack_config": attacked.get("attack_delta"),
        "intervention_record": runner.intervention_records[-1],
        "runtime_seconds": perf_counter() - started,
        "utc_timestamp": datetime.now(timezone.utc).isoformat(),
        "validation_executions": 0,
        "test_executions": 0,
    }
    _save_run(result)
    return result


def run_induction(case_id: str) -> dict[str, Any]:
    """Supply the attacked mediator to the clean receiver context."""
    clean = run_pipeline(case_id, attacked=False)
    attacked = run_pipeline(case_id, attacked=True)
    score = _score(attacked["mediator"]["parsed"])
    return {
        "case_id": case_id, "provenance_type": "LIVE EXECUTION",
        "intervention": "attacked_message_induction",
        "clean_outcome": clean["receiver"],
        "induced_outcome": {"decision": attacked["receiver"]["decision"], "score": score},
        "attacked_mediator": attacked["mediator"],
    }


def _save_run(result: dict[str, Any]) -> Path:
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    path = RUN_ROOT / f"{result['run_id']}.json"
    payload = canonical_json(result)
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return path


def generate_replay(case_id: str, replay_root: Path | None = None) -> dict[str, Any]:
    """Execute clean, attack, and rescue and persist a clearly labelled replay bundle."""
    clean = run_pipeline(case_id, attacked=False)
    attack = run_pipeline(case_id, attacked=True)
    rescue = run_rescue(case_id, clean, attack)
    bundle = {
        "case_id": case_id, "pipeline_version": "aether.demo.pipeline.v1",
        "provenance_type": "REPLAY — VERIFIED PRECOMPUTED EXECUTION",
        "model_id": MODEL_ID, "model_revision": MODEL_REVISION,
        "clean": clean, "attacked": attack, "rescue": rescue,
        "source_commit": _git_commit(), "utc_timestamp": datetime.now(timezone.utc).isoformat(),
    }
    bundle["content_sha256"] = sha256(canonical_json(bundle).encode("utf-8")).hexdigest()
    destination = replay_root or REPLAY_ROOT
    destination.mkdir(parents=True, exist_ok=True)
    (destination / f"{case_id}.json").write_text(json.dumps(bundle, indent=2), encoding="utf-8")
    return bundle


def _git_commit() -> str:
    import subprocess
    return subprocess.run(["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()


def get_run(run_id: str) -> dict[str, Any]:
    """Read one demo-only run artifact."""
    path = RUN_ROOT / f"{run_id}.json"
    if not path.is_file():
        raise KeyError(run_id)
    return json.loads(path.read_text(encoding="utf-8"))


def get_replay(case_id: str) -> dict[str, Any]:
    """Read one verified replay bundle."""
    path = REPLAY_ROOT / f"{case_id}.json"
    if not path.is_file():
        raise KeyError(case_id)
    return json.loads(path.read_text(encoding="utf-8"))
