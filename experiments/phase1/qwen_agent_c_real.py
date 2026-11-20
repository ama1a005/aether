"""Approved real-Qwen Agent C execution with real MCP stdio evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import random
import shutil
import subprocess
import tempfile
import time
from typing import Any, Callable, Mapping, Sequence

import yaml

from experiments.external_bundle import (
    artifact_hashes,
    runtime_metadata,
    sha256_file,
    verify_protocol_approval,
    write_bundle_manifest,
)
from causal.remediation_freeze import frozen_text_hash_matches
from target.mcp.agent_c_client import call_vital_signs


ROOT = Path(__file__).resolve().parents[2]
PROPOSAL = ROOT / "configs/experiments/agent_c_qwen_real_development_v1.yaml"
APPROVAL = ROOT / "results/phase1/protocol_approvals/agent_c_qwen_real_development_v1.json"
EXPECTED_HASH = "9e031fb2911686702e28ec00b54299e01d428a1d2e1676050d0b3dc541d392a7"
EXPECTED_KEYS = {"reviewed_decision", "confidence", "reasons", "incoming_decision_supported"}


def _atomic_json(path: Path, payload: Any) -> None:
    """Write one JSON artifact atomically with durable file contents."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write("\n"); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _atomic_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    """Atomically materialize a JSONL export from authoritative checkpoint rows."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            for row in rows:
                stream.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
            stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def load_protocol() -> dict[str, Any]:
    """Verify human approval and every frozen local input before model access."""
    verify_protocol_approval(PROPOSAL, APPROVAL)
    if not frozen_text_hash_matches(PROPOSAL, EXPECTED_HASH):
        raise PermissionError("real-Qwen Agent C proposal identity differs")
    protocol = yaml.safe_load(PROPOSAL.read_text(encoding="utf-8"))
    if protocol.get("status") != "awaiting_exact_hash_human_review":
        raise ValueError("unexpected real-Qwen Agent C protocol status")
    locks = protocol.get("locks", {})
    if locks.get("validation_executions") != 0 or locks.get("test_executions") != 0:
        raise PermissionError("real-Qwen Agent C protocol opens a protected split")
    inputs = protocol["inputs"]
    for name in ("qwen_ab_rows", "qwen_ab_manifest"):
        record = inputs[name]; path = ROOT / record["path"]
        if not path.is_file() or sha256_file(path) != record["sha256"]:
            raise ValueError(f"real-Qwen Agent C frozen input mismatch: {name}")
    registry = inputs["case_registry"]
    if not frozen_text_hash_matches(ROOT / registry["path"], registry["canonical_lf_sha256"]):
        raise ValueError("real-Qwen Agent C case registry mismatch")
    if len(inputs["case_ids"]) != 24 or inputs["expected_row_count"] != 48:
        raise ValueError("real-Qwen Agent C cohort differs from approval")
    return protocol


def parse_action(raw: str, case_id: str) -> dict[str, Any]:
    """Parse the exact one-tool action without semantic retries."""
    payload = json.loads(raw)
    expected = {"action": "get_vital_signs", "arguments": {"case_id": case_id}}
    if payload != expected:
        raise ValueError("Agent C emitted an invalid or unexpected tool action")
    return payload


def parse_review(raw: str) -> dict[str, Any]:
    """Parse the exact frozen final-review schema."""
    payload = json.loads(raw)
    if not isinstance(payload, dict) or set(payload) != EXPECTED_KEYS:
        raise ValueError("Agent C final review keys differ from the approved schema")
    if payload["reviewed_decision"] not in {"A", "B"}:
        raise ValueError("Agent C reviewed_decision must be A or B")
    confidence = payload["confidence"]
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not math.isfinite(confidence) or not 0 <= confidence <= 1:
        raise ValueError("Agent C confidence must be finite and in [0, 1]")
    reasons = payload["reasons"]
    if not isinstance(reasons, list) or len(reasons) > 8 or any(not isinstance(item, str) for item in reasons):
        raise ValueError("Agent C reasons must be at most eight strings")
    if not isinstance(payload["incoming_decision_supported"], bool):
        raise ValueError("Agent C incoming_decision_supported must be boolean")
    return payload


def _render(template: str, values: Mapping[str, str]) -> str:
    """Render only declared literal placeholders."""
    result = template
    for key, value in values.items():
        result = result.replace("{" + key + "}", value).replace("<" + key + ">", value)
    return result


def verify_snapshot(snapshot: Path, manifest_path: Path,
                    protocol: Mapping[str, Any]) -> dict[str, Any]:
    """Verify the complete local model snapshot before constructing Qwen."""
    snapshot = snapshot.resolve(); manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("model_id") != protocol["model"]["model_id"]:
        raise ValueError("Agent C snapshot manifest model ID differs")
    if manifest.get("resolved_revision") != protocol["model"]["model_revision"]:
        raise ValueError("Agent C snapshot manifest revision differs")
    if manifest.get("tokenizer_revision") != protocol["model"]["tokenizer_revision"]:
        raise ValueError("Agent C tokenizer snapshot revision differs")
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        raise ValueError("Agent C snapshot manifest has no files")
    expected: dict[str, tuple[int, str]] = {}
    for item in files:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            raise ValueError("Agent C snapshot manifest contains a malformed file")
        expected[item["path"]] = (int(item["size"]), str(item["sha256"]))
    observed = {path.relative_to(snapshot).as_posix(): (path.stat().st_size, sha256_file(path))
                for path in sorted(snapshot.rglob("*")) if path.is_file()}
    if observed != expected:
        raise ValueError("Agent C model snapshot differs from its manifest")
    return manifest


def _upload_with_retry(hub: Any, *, attempts: int = 4, **arguments: Any) -> None:
    """Upload one required artifact with bounded visible retries."""
    if attempts < 1:
        raise ValueError("upload attempts must be positive")
    for attempt in range(1, attempts + 1):
        try:
            hub.upload_file(**arguments)
            return
        except Exception as error:
            if attempt == attempts:
                raise RuntimeError(
                    f"Hugging Face upload failed after {attempts} attempts"
                ) from error
            print(
                f"Hugging Face upload attempt {attempt}/{attempts} failed: "
                f"{type(error).__name__}: {error}",
                flush=True,
            )
            time.sleep(2 ** (attempt - 1))


def evaluate_condition(*, protocol: Mapping[str, Any], source: Mapping[str, Any],
                       condition: str, generate: Callable[..., dict[str, Any]],
                       tool_call: Callable[[str], dict[str, Any]]) -> dict[str, Any]:
    """Execute the approved two-generation review for one case-condition."""
    case_id = str(source["case_id"]); incoming = source.get(f"{condition}_receiver_code")
    message = source.get(f"{condition}_message")
    base = {"case_id": case_id, "condition": condition, "incoming_decision": incoming,
            "source_message": message, "source_message_sha256": hashlib.sha256(
                json.dumps(message, sort_keys=True, separators=(",", ":")).encode()).hexdigest()}
    try:
        if incoming not in {"A", "B"} or not isinstance(message, dict) or message.get("valid") is not True:
            raise ValueError("retained source row is invalid")
        prompts = protocol["prompts"]
        action_prompt = _render(prompts["action_user_template"], {
            "case_id": case_id, "condition": condition, "incoming_decision": incoming,
            "mediator_message_json": json.dumps(message, sort_keys=True, separators=(",", ":")),
        })
        action = generate(prompts["system_template"], action_prompt,
                          int(protocol["generation"]["action_max_new_tokens"]))
        parsed_action = parse_action(action["text"], case_id)
        tool = tool_call(case_id)
        final_prompt = _render(prompts["final_user_template"], {
            "tool_result_json": json.dumps(tool["response"], sort_keys=True, separators=(",", ":"))})
        final = generate(prompts["system_template"], final_prompt,
                         int(protocol["generation"]["final_max_new_tokens"]),
                         prior_user=action_prompt, prior_assistant=action["text"])
        review = parse_review(final["text"])
        return {**base, "valid": True, "error": None, "action_prompt": action_prompt,
                "action_prompt_token_ids": action["prompt_token_ids"], "raw_action": action["text"],
                "action_token_ids": action["generation_token_ids"], "parsed_action": parsed_action,
                "mcp": tool, "final_prompt": final_prompt,
                "final_prompt_token_ids": final["prompt_token_ids"], "raw_review": final["text"],
                "review_token_ids": final["generation_token_ids"], **review}
    except (ValueError, TypeError, RuntimeError, json.JSONDecodeError) as error:
        return {**base, "valid": False,
                "error": {"type": type(error).__name__, "message": str(error)}}


def summarize(rows: Sequence[Mapping[str, Any]], ground_truth: Mapping[str, str]) -> dict[str, Any]:
    """Compute frozen all-row denominators; invalid reviews count as incorrect."""
    total = len(rows)
    incoming_correct = 0; reviewed_correct = 0; corrections = 0; incoming_errors = 0
    regressions = 0; incoming_right = 0
    by_condition = {"clean": [0, 0], "attacked": [0, 0]}
    paired = []
    incoming_only = 0
    reviewed_only = 0
    for row in rows:
        truth = ground_truth[row["case_id"]]
        inc = row.get("incoming_decision") == truth
        rev = row.get("valid") is True and row.get("reviewed_decision") == truth
        incoming_correct += int(inc); reviewed_correct += int(rev)
        incoming_errors += int(not inc); incoming_right += int(inc)
        corrections += int((not inc) and rev); regressions += int(inc and not rev)
        incoming_only += int(inc and not rev); reviewed_only += int((not inc) and rev)
        by_condition[row["condition"]][0] += int(rev); by_condition[row["condition"]][1] += 1
        paired.append(int(rev) - int(inc))
    difference = (reviewed_correct - incoming_correct) / total
    discordant = incoming_only + reviewed_only
    if discordant:
        lower = min(incoming_only, reviewed_only)
        mcnemar = min(1.0, 2.0 * sum(math.comb(discordant, index)
                      for index in range(lower + 1)) / (2 ** discordant))
    else:
        mcnemar = 1.0
    generator = random.Random(0)
    bootstrap = sorted(sum(paired[generator.randrange(total)] for _ in range(total)) / total
                       for _ in range(10_000))
    interval = [bootstrap[249], bootstrap[9749]]
    return {"overall": "PASS" if total == 48 else "INCOMPLETE",
            "execution_pass_semantics": "integrity_and_completion_only",
            "total_rows": total, "valid_rows": sum(row.get("valid") is True for row in rows),
            "invalid_rows": sum(row.get("valid") is not True for row in rows),
            "incoming_decision_accuracy_all_rows": incoming_correct / total,
            "reviewed_decision_accuracy_all_rows": reviewed_correct / total,
            "paired_accuracy_difference": difference,
            "invalid_fraction": sum(row.get("valid") is not True for row in rows) / total,
            "correction_fraction_among_incoming_errors": corrections / incoming_errors if incoming_errors else None,
            "regression_fraction_among_incoming_correct": regressions / incoming_right if incoming_right else None,
            "clean_reviewed_accuracy": by_condition["clean"][0] / by_condition["clean"][1],
            "attacked_reviewed_accuracy": by_condition["attacked"][0] / by_condition["attacked"][1],
            "mcnemar_exact_p_value": mcnemar,
            "paired_bootstrap_95_percent_ci": interval,
            "validation_executions": 0, "test_executions": 0,
            "claim_boundary": str(load_protocol()["claim_boundary"])}


def _generator(snapshot: Path, protocol: Mapping[str, Any]) -> Callable[..., dict[str, Any]]:
    """Load the exact local snapshot and return deterministic Qwen generation."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(snapshot, local_files_only=True, trust_remote_code=False)
    model = AutoModelForCausalLM.from_pretrained(
        snapshot, local_files_only=True, trust_remote_code=False, dtype=torch.float16).to("cuda:0").eval()
    def generate(system: str, user: str, maximum: int, *, prior_user: str | None = None,
                 prior_assistant: str | None = None) -> dict[str, Any]:
        messages = [{"role": "system", "content": system}]
        if prior_user is not None or prior_assistant is not None:
            if prior_user is None or prior_assistant is None:
                raise ValueError("generation history must contain both prior turns")
            messages.extend([{"role": "user", "content": prior_user},
                             {"role": "assistant", "content": prior_assistant}])
        messages.append({"role": "user", "content": user})
        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        encoded = tokenizer(text, return_tensors="pt", add_special_tokens=False)
        prompt_ids = encoded["input_ids"][0].tolist(); encoded = {k: v.to("cuda:0") for k, v in encoded.items()}
        with torch.inference_mode():
            output = model.generate(**encoded, do_sample=False, max_new_tokens=maximum,
                                    pad_token_id=tokenizer.eos_token_id)
        generated = output[0, len(prompt_ids):].tolist()
        return {"text": tokenizer.decode(generated, skip_special_tokens=True).strip(),
                "prompt_token_ids": prompt_ids, "generation_token_ids": generated}
    return generate


def run(*, output: Path, snapshot: Path, snapshot_manifest: Path, checkpoint_repo: str,
        checkpoint_path: str, resume: bool = False) -> Path:
    """Execute or resume the approved 48-row development experiment."""
    protocol = load_protocol()
    root = ROOT.resolve(); output = output.resolve()
    if output == root or root in output.parents:
        raise ValueError("real-Qwen Agent C output must be outside the source checkout")
    status = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=ROOT,
                            check=True, capture_output=True, text=True).stdout
    if status.strip():
        raise RuntimeError("real-Qwen Agent C requires a clean source checkout")
    if not checkpoint_repo or "/" not in checkpoint_repo or not checkpoint_path:
        raise ValueError("a private remote checkpoint repository and path are required")
    from huggingface_hub import HfApi
    hub = HfApi(token=os.environ.get("HF_TOKEN"))
    repository_info = hub.repo_info(repo_id=checkpoint_repo, repo_type="dataset")
    if not repository_info.private:
        raise PermissionError("real-Qwen Agent C checkpoint repository must be private")
    snapshot_record = verify_snapshot(snapshot, snapshot_manifest, protocol)
    plan_sha256 = hashlib.sha256(json.dumps({
        "proposal_sha256": EXPECTED_HASH,
        "git_commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
                                     capture_output=True, text=True).stdout.strip(),
        "model_revision": snapshot_record["resolved_revision"],
        "input_hashes": {key: value.get("sha256", value.get("canonical_lf_sha256"))
                         for key, value in protocol["inputs"].items()
                         if isinstance(value, dict) and "path" in value},
    }, sort_keys=True).encode()).hexdigest()
    checkpoint = output / "checkpoint_state.json"
    if output.exists() and not resume:
        raise FileExistsError(output)
    if resume and not checkpoint.is_file():
        raise FileNotFoundError("resume requires checkpoint_state.json")
    output.mkdir(parents=True, exist_ok=resume)
    shutil.copy2(snapshot_manifest, output / "model_snapshot_manifest.json")
    _atomic_json(output / "preflight.json", {"overall": "PASS", "model_accessed": False,
        "proposal_sha256": EXPECTED_HASH, "utc_timestamp": datetime.now(timezone.utc).isoformat(),
        "validation_executions": 0, "test_executions": 0})
    source_rows = json.loads((ROOT / protocol["inputs"]["qwen_ab_rows"]["path"]).read_text(encoding="utf-8"))
    wanted = set(protocol["inputs"]["case_ids"])
    ordered = [(row, condition) for row in source_rows if row.get("case_id") in wanted
               for condition in ("clean", "attacked")]
    if len(ordered) != 48:
        raise ValueError("frozen source did not resolve to exactly 48 ordered rows")
    prior = json.loads(checkpoint.read_text(encoding="utf-8")) if checkpoint.exists() else {
        "proposal_sha256": EXPECTED_HASH, "plan_sha256": plan_sha256, "rows": []}
    if prior.get("proposal_sha256") != EXPECTED_HASH or prior.get("plan_sha256") != plan_sha256:
        raise ValueError("checkpoint belongs to a different approved execution plan")
    rows = prior.get("rows")
    if not isinstance(rows, list) or [(r.get("case_id"), r.get("condition")) for r in rows] != [
            (r[0]["case_id"], r[1]) for r in ordered[:len(rows)]]:
        raise ValueError("checkpoint is not an exact ordered prefix")
    generate = _generator(snapshot, protocol)
    registry_path = ROOT / protocol["inputs"]["case_registry"]["path"]
    for source, condition in ordered[len(rows):]:
        row = evaluate_condition(protocol=protocol, source=source, condition=condition,
            generate=generate, tool_call=lambda case_id: call_vital_signs(registry_path, case_id))
        rows.append(row); _atomic_json(checkpoint, {"proposal_sha256": EXPECTED_HASH,
                                                    "plan_sha256": plan_sha256, "rows": rows})
        _upload_with_retry(
            hub, path_or_fileobj=checkpoint, path_in_repo=checkpoint_path,
            repo_id=checkpoint_repo, repo_type="dataset",
            commit_message=f"Agent C checkpoint {len(rows)}/48",
        )
    registry = json.loads(registry_path.read_text(encoding="utf-8"))["cases"]
    truth = {row["case_id"]: ("A" if row["ground_truth_decision"] == "ESCALATE" else "B")
             for row in registry if row["case_id"] in wanted}
    summary = summarize(rows, truth); _atomic_json(output / "summary.json", summary)
    _atomic_jsonl(output / "raw_reviews.jsonl", rows)
    metadata = runtime_metadata(repository=ROOT, experiment_id="P0_agent_c_real_qwen15b_development",
        run_id=output.name, dataset_manifest_hashes={k: v.get("sha256", v.get("canonical_lf_sha256"))
        for k, v in protocol["inputs"].items() if isinstance(v, dict) and "path" in v},
        model_id=protocol["model"]["model_id"], model_revision=protocol["model"]["model_revision"],
        tokenizer_revision=protocol["model"]["tokenizer_revision"], seeds=[0], config_file=PROPOSAL,
        evidence_kind="qwen_agent_c_real")
    metadata.update({"proposal_sha256": EXPECTED_HASH, "raw_output_path": "raw_reviews.jsonl",
                     "prompt_versions": {"agent_c": protocol["prompts"]["prompt_version"]}})
    _atomic_json(output / "manifest.json", metadata)
    _atomic_json(output / "archive_contents.json", artifact_hashes(output, exclude=("archive_contents.json", "bundle_manifest.json")))
    write_bundle_manifest(output, metadata)
    return output / "summary.json"


def main() -> None:
    """CLI for approved real-Qwen Agent C execution."""
    parser = argparse.ArgumentParser(); parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model-snapshot", type=Path, required=True)
    parser.add_argument("--snapshot-manifest", type=Path, required=True)
    parser.add_argument("--checkpoint-repo", required=True); parser.add_argument("--checkpoint-path", required=True)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(); print(run(output=args.output, snapshot=args.model_snapshot,
        snapshot_manifest=args.snapshot_manifest, checkpoint_repo=args.checkpoint_repo,
        checkpoint_path=args.checkpoint_path, resume=args.resume))


if __name__ == "__main__":
    main()
