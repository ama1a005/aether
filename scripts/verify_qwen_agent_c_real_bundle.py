"""Independently verify an approved real-Qwen Agent C evidence bundle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from experiments.external_bundle import artifact_hashes, verify_bundle
from experiments.phase1.qwen_agent_c_real import EXPECTED_HASH, load_protocol, summarize


def verify(root: Path) -> dict[str, Any]:
    """Reject incomplete, altered, mock, protected-split or overstated bundles."""
    root = root.resolve(); bundle = verify_bundle(root, expected_kind="qwen_agent_c_real")
    protocol = load_protocol(); required = set(protocol["artifacts"]["required"])
    missing = sorted(name for name in required if not (root / name).is_file())
    if missing:
        raise FileNotFoundError(f"real-Qwen Agent C bundle lacks required artifacts: {missing}")
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    summary = json.loads((root / "summary.json").read_text(encoding="utf-8"))
    checkpoint = json.loads((root / "checkpoint_state.json").read_text(encoding="utf-8"))
    preflight = json.loads((root / "preflight.json").read_text(encoding="utf-8"))
    declared = json.loads((root / "archive_contents.json").read_text(encoding="utf-8"))
    observed = artifact_hashes(root, exclude=("archive_contents.json", "bundle_manifest.json"))
    if declared != observed:
        raise ValueError("real-Qwen Agent C archive inventory differs")
    rows = checkpoint.get("rows")
    if (checkpoint.get("proposal_sha256") != EXPECTED_HASH
            or not isinstance(checkpoint.get("plan_sha256"), str)
            or len(checkpoint["plan_sha256"]) != 64
            or not isinstance(rows, list) or len(rows) != 48):
        raise ValueError("real-Qwen Agent C checkpoint is incomplete or belongs to another protocol")
    raw_rows = [json.loads(line) for line in (root / "raw_reviews.jsonl").read_text(encoding="utf-8").splitlines()]
    if raw_rows != rows:
        raise ValueError("real-Qwen Agent C raw rows differ from the checkpoint")
    expected_keys = [(case_id, condition) for case_id in protocol["inputs"]["case_ids"]
                     for condition in ("clean", "attacked")]
    if [(row.get("case_id"), row.get("condition")) for row in rows] != expected_keys:
        raise ValueError("real-Qwen Agent C rows differ from the frozen order")
    for row in rows:
        if row.get("valid") is True:
            mcp = row.get("mcp", {})
            envelope = mcp.get("envelope", {}) if isinstance(mcp, dict) else {}
            tools = mcp.get("discovered_tools", []) if isinstance(mcp, dict) else []
            if (envelope.get("transport") != "stdio" or envelope.get("server") != "aether-agent-c-vitals"
                    or [item.get("name") for item in tools].count("get_vital_signs") != 1):
                raise ValueError("real-Qwen Agent C valid row lacks verified MCP stdio provenance")
            if row.get("reviewed_decision") not in {"A", "B"}:
                raise ValueError("real-Qwen Agent C valid row lacks a reviewed decision")
        elif not isinstance(row.get("error"), dict):
            raise ValueError("real-Qwen Agent C invalid row lacks a retained error")
    registry_path = Path(__file__).resolve().parents[1] / protocol["inputs"]["case_registry"]["path"]
    registry = json.loads(registry_path.read_text(encoding="utf-8"))["cases"]
    wanted = set(protocol["inputs"]["case_ids"])
    truth = {row["case_id"]: ("A" if row["ground_truth_decision"] == "ESCALATE" else "B")
             for row in registry if row["case_id"] in wanted}
    if summarize(rows, truth) != summary:
        raise ValueError("real-Qwen Agent C summary differs from independently recomputed metrics")
    if summary.get("overall") != "PASS" or preflight.get("overall") != "PASS":
        raise ValueError("real-Qwen Agent C run is not complete")
    if any(record.get("validation_executions") != 0 or record.get("test_executions") != 0
           for record in (summary, manifest, preflight)):
        raise ValueError("real-Qwen Agent C bundle accessed a protected split")
    if manifest.get("model_id") != protocol["model"]["model_id"] or manifest.get("model_revision") != protocol["model"]["model_revision"]:
        raise ValueError("real-Qwen Agent C model identity differs")
    return {"verified": True, "experiment_id": bundle.experiment_id, "run_id": bundle.run_id,
            "row_count": len(rows), "condition_rows": len(rows), "valid_count": summary["valid_rows"],
            "invalid_count": summary["invalid_rows"], "claim_boundary": summary["claim_boundary"]}


def main() -> None:
    """Verify one retained real-Qwen Agent C bundle."""
    parser = argparse.ArgumentParser(); parser.add_argument("root", type=Path); args = parser.parse_args()
    print(json.dumps(verify(args.root), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
