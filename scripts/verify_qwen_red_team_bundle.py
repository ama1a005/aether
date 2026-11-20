"""Independently verify a retained real-Qwen red-team campaign bundle."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

from attacks.delta_validator import AttackDelta, validate_delta
from experiments.external_bundle import verify_bundle


def verify(root: Path) -> dict[str, Any]:
    """Rebuild admission checks and metrics from raw rows without runner state."""
    generic = verify_bundle(root, expected_kind="qwen_red_team")
    plan = json.loads((root / "plan.json").read_text(encoding="utf-8"))
    provenance = json.loads((root / "corpus_provenance.json").read_text(encoding="utf-8"))
    summary = json.loads((root / "campaign_summary.json").read_text(encoding="utf-8"))
    identity = plan.get("identity", {})
    expected = {str(row["attempt_id"]): row for row in identity.get("plan", [])}
    if not expected or provenance != identity.get("corpus_provenance"):
        raise ValueError("plan or corpus provenance is incomplete or mismatched")
    rows: list[dict[str, Any]] = []
    for path in sorted((root / "attempts").glob("*.json")):
        row = json.loads(path.read_text(encoding="utf-8"))
        if row.get("attempt_id") not in expected:
            raise ValueError("attempt ledger contains an unknown attempt")
        rows.append(row)
    if len(rows) != len(expected) or {row["attempt_id"] for row in rows} != set(expected):
        raise ValueError("attempt ledger is missing or duplicates a planned pair")
    calls = 0
    successes = 0
    errors = 0
    for row in rows:
        if row.get("status") not in {"complete", "error"}:
            raise ValueError("incomplete started attempt is not admissible")
        calls += int(row.get("target_calls", -1))
        errors += row.get("status") == "error"
        successes += row.get("success") is True
        clean, attacked, delta = row.get("clean"), row.get("attacked"), row.get("delta")
        if not isinstance(clean, dict) or not isinstance(attacked, dict):
            raise ValueError("every admitted pair requires raw clean/attacked traces")
        if row.get("status") == "complete" and not isinstance(delta, dict):
            raise ValueError("every complete attempt requires a validated delta")
        if clean.get("case_id") != attacked.get("case_id") or clean.get("case_id") != expected[row["attempt_id"]]["case"]["case_id"]:
            raise ValueError("clean/attacked case identity mismatch")
        if not clean.get("model_ids") or clean.get("model_ids") != attacked.get("model_ids"):
            raise ValueError("model identity is absent or changes inside a pair")
        if any("rule" in str(value).lower() or "fixture" in str(value).lower() for value in clean["model_ids"].values()):
            raise ValueError("synthetic backend marker in a real-Qwen bundle")
        if delta is not None:
            ok, reasons = validate_delta(AttackDelta(**delta), require_plan_binding=True)
            if not ok or delta["plan_fingerprint"] != plan["fingerprint"] or delta["corpus_hash"] != provenance["corpus_hash"]:
                raise ValueError(f"invalid bound delta: {reasons}")
        if not clean.get("tool_calls") or not attacked.get("tool_calls"):
            raise ValueError("raw prompt/tool provenance is missing")
        if not all("sender_prompt" in trace["tool_calls"][0] and "receiver_prompt" in trace["tool_calls"][0]
                   for trace in (clean, attacked)):
            raise ValueError("raw prompt provenance is missing")
    if calls != summary.get("target_calls") or calls > identity["config"]["max_target_calls"]:
        raise ValueError("model-call ledger does not match the plan budget")
    if summary["overall"]["eligible_attempts"] != len(rows) or summary["overall"]["successes"] != successes:
        raise ValueError("stored campaign metrics differ from raw rows")
    return {"overall": "PASS", "evidence_valid": True, "execution_complete": True,
            "scientific_outcome": "negative" if successes == 0 else "observed_targeted_success",
            "eligible_attempts": len(rows), "successes": successes, "errors": errors,
            "asr": successes / len(rows), "model_calls": calls, "generic": asdict(generic)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = verify(args.root)
    rendered = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
