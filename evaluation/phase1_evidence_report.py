"""Generate the final Phase-1 evidence index only after every prerequisite passes."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.audit_phase1_completion import DEFAULT_CONFIG, ROOT, audit


FINAL_GATE = "final_verified_report"


def generate(repository: Path, config: Path, output: Path) -> Path:
    """Write a hash-indexed report manifest after all non-report gates pass."""
    report = audit(repository, config)
    prerequisites = [row for row in report["gates"] if row["id"] != FINAL_GATE]
    incomplete = [row["id"] for row in prerequisites if row["status"] not in {"PASS", "NOT_APPLICABLE"}]
    if incomplete:
        raise ValueError(f"final report rejects incomplete prerequisite gates: {incomplete}")
    if output.exists():
        raise FileExistsError(f"final report output already exists: {output}")
    artifacts: dict[str, dict[str, Any]] = {}
    repository = repository.resolve()
    for row in prerequisites:
        path = Path(row["path"])
        files = [path] if path.is_file() else sorted(item for item in path.rglob("*") if item.is_file())
        if not files and row["status"] == "PASS":
            raise ValueError(f"passing gate has no evidence files: {row['id']}")
        hashes = {}
        for artifact in files:
            digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
            hashes[str(artifact.resolve().relative_to(repository)).replace("\\", "/")] = digest
        artifacts[row["id"]] = {"status": row["status"], "hashes": hashes, "reasons": row["reasons"]}
    output.mkdir(parents=True)
    manifest = {
        "schema_version": "aether.phase1-final-report.v1", "overall": "PASS",
        "incomplete_runs_rejected": True, "utc_timestamp": datetime.now(timezone.utc).isoformat(),
        "completion_config": str(config), "prerequisite_gate_count": len(prerequisites),
        "evidence": artifacts, "claim_boundary": report["claim_boundary"],
    }
    destination = output / "report_manifest.json"
    destination.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return destination


def main() -> None:
    """Run final evidence-index generation from the command line."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", type=Path, default=ROOT)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=ROOT / "results/phase1/final_report")
    arguments = parser.parse_args()
    print(generate(arguments.repository, arguments.config, arguments.output))


if __name__ == "__main__":
    main()
