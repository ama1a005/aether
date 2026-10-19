"""Freeze hashes for validated demo fixtures and executed replay bundles."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

from demo.backend.repository import CASE_PATH, load_cases
from paired_trace.schemas import canonical_json


def main() -> None:
    """Write the review-only manifest without touching research datasets."""
    entries = []
    for case in load_cases():
        replay_path = Path("demo/artifacts/replays") / f"{case.case_id}.json"
        replay = json.loads(replay_path.read_text(encoding="utf-8"))
        entries.append({
            "case_id": case.case_id,
            "case_schema_sha256": sha256(canonical_json(case.to_dict()).encode()).hexdigest(),
            "expected_research_action": case.expected_action,
            "tools": case.available_tools,
            "attack_target": case.primary_attack_target,
            "clean_verified": replay["clean"]["correct"],
            "attacked_verified": replay["attacked"]["receiver"]["decision"] != replay["clean"]["receiver"]["decision"],
            "rescue_verified": replay["rescue"]["normalized_recovery"] == 1.0,
            "artifact_id": replay["content_sha256"],
            "artifact_path": str(replay_path).replace("\\", "/"),
        })
    payload = {
        "manifest_version": "aether.demo.case-manifest.v1",
        "dataset_origin": "aether_intermediate_review_demo",
        "scientific_dataset": False,
        "case_registry_path": str(CASE_PATH).replace("\\", "/"),
        "case_count": len(entries),
        "validation_executions": 0,
        "test_executions": 0,
        "cases": entries,
    }
    Path("demo/cases/demo_case_manifest.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
