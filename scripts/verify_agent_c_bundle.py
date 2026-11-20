"""Independently verify paired development-only Agent C evidence bundles."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from experiments.external_bundle import verify_bundle

EXPECTED_CASE_COUNT = 24


def verify(root: Path) -> dict[str, Any]:
    """Check artifact hashes, split boundary and exact unique paired coverage."""
    root = Path(root).resolve()
    bundle = verify_bundle(root, expected_kind="qwen_agent_c")
    raw = json.loads((root / "raw_reviews.json").read_text(encoding="utf-8"))
    summary = json.loads((root / "summary.json").read_text(encoding="utf-8"))
    manifest = json.loads((root / "bundle_manifest.json").read_text(encoding="utf-8"))
    rows = raw.get("rows")
    if not isinstance(rows, list) or not rows:
        raise ValueError("Agent-C raw reviews are empty or malformed")
    if len(rows) != EXPECTED_CASE_COUNT * 2:
        raise ValueError(f"Agent-C evidence must contain exactly {EXPECTED_CASE_COUNT * 2} paired rows")
    keys = [(str(row.get("case_id")), row.get("condition")) for row in rows]
    if len(keys) != len(set(keys)) or any(condition not in {"clean", "attacked"} for _, condition in keys):
        raise ValueError("Agent-C evidence has duplicate or unexpected case-condition rows")
    cohort = {case_id for case_id, _ in keys}
    expected = {(case_id, condition) for case_id in cohort for condition in ("clean", "attacked")}
    if set(keys) != expected:
        raise ValueError("Agent-C evidence does not contain exactly paired clean/attacked rows")
    if len(cohort) != EXPECTED_CASE_COUNT:
        raise ValueError(f"Agent-C evidence must cover exactly {EXPECTED_CASE_COUNT} development cases")
    for row in rows:
        case_id, condition = str(row.get("case_id")), str(row.get("condition"))
        source = row.get("source_row")
        if not isinstance(source, dict) or source.get("case_id") != case_id or source.get("split") != "development":
            raise ValueError("Agent-C evidence contains a missing, mismatched, or protected-split source row")
        expected_input = {
            "message": source.get(f"{condition}_message"),
            "receiver_code": source.get(f"{condition}_receiver_code"),
            "receiver_prompt": source.get(f"{condition}_receiver_prompt"),
            "receiver_prompt_token_ids": source.get(f"{condition}_receiver_prompt_token_ids"),
        }
        if row.get("input") != expected_input:
            raise ValueError("Agent-C evidence inputs differ from the retained source trace")
        if not isinstance(row.get("valid"), bool):
            raise ValueError("Agent-C row lacks an explicit valid/invalid status")
        message = source.get(f"{condition}_message")
        incoming = source.get(f"{condition}_receiver_code")
        source_valid = (source.get("eligible") is True
                        and source.get(f"{condition}_message_valid") is True
                        and isinstance(message, dict) and message.get("valid") is True
                        and incoming in ("A", "B"))
        if row["valid"] is not source_valid:
            raise ValueError("Agent-C valid/invalid status differs from frozen source eligibility")
        latency = row.get("latency_ms")
        if isinstance(latency, bool) or not isinstance(latency, (int, float)) or not math.isfinite(latency) or latency < 0:
            raise ValueError("Agent-C row has an invalid latency value")
        if source_valid:
            expected_ground_truth = {"A": "ESCALATE", "B": "DO_NOT_ESCALATE"}.get(
                source.get("ground_truth_code"))
            if (row.get("incoming_decision") != ("ESCALATE" if incoming == "A" else "DO_NOT_ESCALATE")
                    or row.get("ground_truth_decision") != expected_ground_truth
                    or row.get("reviewed_decision") not in {"ESCALATE", "DO_NOT_ESCALATE"}
                    or not isinstance(row.get("tool_calls"), list)
                    or not isinstance(row.get("review"), dict)
                    or row["review"].get("incoming_decision") != row.get("incoming_decision")
                    or row["review"].get("reviewed_decision") != row.get("reviewed_decision")
                    or row["review"].get("tool_calls") != row.get("tool_calls")
                    or not isinstance(row.get("incoming_correct"), bool)
                    or not isinstance(row.get("reviewed_correct"), bool)
                    or row.get("incoming_correct") != (row.get("incoming_decision") == expected_ground_truth)
                    or row.get("reviewed_correct") != (row.get("reviewed_decision") == expected_ground_truth)):
                raise ValueError("Agent-C valid row lacks its parsed review, outcome, or tool-call evidence")
        elif not isinstance(row.get("error"), str) or not row["error"]:
            raise ValueError("Agent-C invalid row lacks a retained error reason")
    if manifest.get("validation_executions") != 0 or manifest.get("test_executions") != 0:
        raise ValueError("Agent-C bundle accessed a protected split")
    if summary.get("overall") != "SUPPORTING_EVIDENCE_ONLY" or summary.get("validation_executions") != 0 or summary.get("test_executions") != 0:
        raise ValueError("Agent-C summary overstates claims or omits split locks")
    counts = raw.get("counts", {})
    valid_rows = [row for row in rows if row["valid"]]
    computed_counts = {
        "total": len(rows), "valid": len(valid_rows), "invalid": len(rows) - len(valid_rows),
        "incoming_correct": sum(row["incoming_correct"] for row in valid_rows),
        "reviewed_correct": sum(row["reviewed_correct"] for row in valid_rows),
    }
    if counts != computed_counts:
        raise ValueError("Agent-C raw summary counts differ from its per-row evidence")
    if any(summary.get(key) != counts.get(key) for key in (
            "total", "valid", "invalid", "incoming_correct", "reviewed_correct")):
        raise ValueError("Agent-C summary metrics differ from the raw review counts")
    return {"verified": True, "experiment_id": bundle.experiment_id, "run_id": bundle.run_id,
            "case_count": len(cohort), "condition_rows": len(rows),
            "claim_boundary": "Retained real-Qwen A/B traces with deterministic clean-tool Agent-C review; supporting evidence only."}


def main() -> None:
    """Verify one external Agent-C bundle."""
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.root), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
