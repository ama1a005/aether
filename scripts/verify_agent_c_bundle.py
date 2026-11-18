"""Independently verify paired development-only Agent C evidence bundles."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from experiments.external_bundle import verify_bundle


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
    keys = [(str(row.get("case_id")), row.get("condition")) for row in rows]
    if len(keys) != len(set(keys)) or any(condition not in {"clean", "attacked"} for _, condition in keys):
        raise ValueError("Agent-C evidence has duplicate or unexpected case-condition rows")
    cohort = {case_id for case_id, _ in keys}
    expected = {(case_id, condition) for case_id in cohort for condition in ("clean", "attacked")}
    if set(keys) != expected:
        raise ValueError("Agent-C evidence does not contain exactly paired clean/attacked rows")
    if any(not row.get("case_id") or row.get("input") is None for row in rows):
        raise ValueError("Agent-C evidence omitted source decision/message inputs")
    if manifest.get("validation_executions") != 0 or manifest.get("test_executions") != 0:
        raise ValueError("Agent-C bundle accessed a protected split")
    if summary.get("overall") != "SUPPORTING_EVIDENCE_ONLY" or summary.get("validation_executions") != 0 or summary.get("test_executions") != 0:
        raise ValueError("Agent-C summary overstates claims or omits split locks")
    counts = raw.get("counts", {})
    if counts.get("total") != len(rows) or counts.get("valid", 0) + counts.get("invalid", 0) != len(rows):
        raise ValueError("Agent-C summary counts differ from raw rows")
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
