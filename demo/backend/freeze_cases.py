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
        replay_path = Path("demo/artifacts/replays_ptbxl_v1") / f"{case.case_id}.json"
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
        "manifest_version": "aether.demo.case-manifest.v2.ptbxl",
        "dataset_origin": "ptbxl_v1.0.3_physionet",
        "scientific_dataset": False,
        "source_dataset_is_official": True,
        "official_benchmark_execution": False,
        "action_labels_are_aether_derived": True,
        "case_registry_path": "demo/cases/ptbxl_demo_cases.json",
        "case_count": len(entries),
        "validation_executions": 0,
        "test_executions": 0,
        "cases": entries,
    }
    Path("demo/cases/demo_case_manifest.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
