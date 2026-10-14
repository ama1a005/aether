"""Validate the pinned TAMAS dataset adapter without changing native execution semantics."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

from benchmarks.tamas import load_tamas_cases
from experiments.manifest import sha256_file

ROOT = Path(".cache/benchmarks/TAMAS")
COMMIT = "545c112af9aab93b7ef2b0b60831d93c81c365c3"


def main() -> None:
    """Load all identities, serialize ten native records, and declare execution limits."""
    cases = load_tamas_cases(ROOT / "data")
    counts = Counter(case.attack_type for case in cases)
    if len(cases) != 300 or set(counts.values()) != {50}:
        raise ValueError("pinned TAMAS release identity changed")
    output_dir = Path("results/phase1/tamas/smoke")
    output_dir.mkdir(parents=True, exist_ok=True)
    rows_path = output_dir / "adapter_rows.json"
    rows_path.write_text(json.dumps([{"case_id": case.case_id, "attack_type": case.attack_type, "scenario": case.scenario, "payload": case.payload, "evaluation_origin": case.evaluation_origin} for case in cases[:10]], indent=2), encoding="utf-8")
    data_files = sorted((ROOT / "data").glob("*/*.json"))
    summary = {"result_state": "SMOKE", "evaluation_origin": "tamas_official_adapter", "official_repository": "https://github.com/microsoft/TAMAS", "official_commit": COMMIT, "license": {"code": "MIT", "data": "CDLA-Permissive-2.0"}, "loaded_count": len(cases), "counts_by_attack": dict(counts), "serialized_smoke_count": 10, "native_execution_status": "not_run", "incompatibilities": ["official harness targets AutoGen or CrewAI, not the AETHER two-agent harness", "official evaluators require provider API credentials and include LLM-based assessment", "running through AETHER would be transformed, not official-compatible"], "data_tree_sha256": sha256("".join(f"{path.relative_to(ROOT)}:{sha256_file(path)}\n" for path in data_files).encode()).hexdigest(), "utc_timestamp": datetime.now(timezone.utc).isoformat()}
    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    manifest = {"manifest_version": "1.0.0", "result_state": "SMOKE", "evaluation_origin": "tamas_official_adapter", "official_commit": COMMIT, "artifacts": {str(rows_path): sha256_file(rows_path), str(summary_path): sha256_file(summary_path)}}
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
