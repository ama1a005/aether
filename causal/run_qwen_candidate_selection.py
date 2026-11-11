"""Execute the frozen discovery-only QCI-1 candidate selector."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import subprocess
import sys
from typing import Any

from causal.qwen_candidate_selection import load_protocol, select_candidates
from experiments.manifest import sha256_file

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "configs/causal_candidates/qwen_1_5b_dcap1_intervention_v1.json"
QUALIFICATION_ROWS = ROOT / "results/phase1/model_qualification/qwen15b_kaggle_20261110/mq_g1_rows.json"
DEFAULT_OUTPUT = ROOT / "results/phase1/candidate_selection/qwen15b_qci1"


def _write_json(path: Path, value: Any) -> None:
    """Write strict, stable JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def _git(*arguments: str) -> str:
    """Return required Git metadata."""
    return subprocess.run(
        ["git", *arguments], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def _verify_discovery_artifacts(
    activation_root: Path, records: list[dict[str, Any]], protocol: dict[str, Any]
) -> dict[str, str]:
    """Hash-verify exactly the discovery tensors without opening audit tensors."""
    discovery = set(protocol["discovery_case_ids"])
    selected = [record for record in records if record["case_id"] in discovery]
    expected = len(discovery) * 2 * 2
    if len(selected) != expected:
        raise ValueError(f"expected {expected} discovery activation records, found {len(selected)}")
    if any(record.get("partition") != "discovery" for record in selected):
        raise ValueError("a selected activation record is not labelled discovery")
    hashes: dict[str, str] = {}
    for record in selected:
        name = Path(record["path"]).name
        path = activation_root / name
        if not path.is_file():
            raise FileNotFoundError(f"missing discovery activation artifact: {name}")
        observed = sha256_file(path)
        if observed != record["sha256"]:
            raise ValueError(f"discovery activation hash mismatch: {name}")
        hashes[name] = observed
    if len(hashes) != expected:
        raise ValueError("duplicate discovery activation artifact names")
    return dict(sorted(hashes.items()))


def run(activation_root: Path, output_root: Path) -> dict[str, Any]:
    """Run the frozen selector and write an auditable discovery-only result."""
    protocol = load_protocol(PROTOCOL_PATH)
    dcap_root = ROOT / protocol["dcap_directory"]
    if sha256_file(dcap_root / "summary.json") != protocol["dcap_summary_sha256"]:
        raise ValueError("DCAP summary differs from the frozen QCI input")
    if sha256_file(dcap_root / "manifest.json") != protocol["dcap_manifest_sha256"]:
        raise ValueError("DCAP manifest differs from the frozen QCI input")
    summary = json.loads((dcap_root / "summary.json").read_text(encoding="utf-8"))
    if summary.get("overall") != "PASS":
        raise ValueError("DCAP prerequisite did not pass")
    if summary.get("validation_executions") != 0 or summary.get("test_executions") != 0:
        raise ValueError("DCAP prerequisite accessed a locked split")
    records = json.loads((dcap_root / "activation_artifacts.json").read_text(encoding="utf-8"))
    artifact_hashes = _verify_discovery_artifacts(activation_root, records, protocol)
    rows = json.loads(QUALIFICATION_ROWS.read_text(encoding="utf-8"))
    result = select_candidates(activation_root, rows, protocol)
    result.update({
        "schema_version": "aether.qci-candidate-selection.v1",
        "experiment_id": protocol["experiment_id"],
        "run_id": f"{protocol['experiment_id']}_seed42",
        "utc_timestamp": datetime.now(timezone.utc).isoformat(),
        "model_id": protocol["model_id"],
        "model_revision": protocol["model_revision"],
        "protocol_sha256": sha256_file(PROTOCOL_PATH),
        "qualification_rows_sha256": sha256_file(QUALIFICATION_ROWS),
        "discovery_artifact_hashes": artifact_hashes,
        "validation_executions": 0,
        "test_executions": 0,
        "next_state": "READY_FOR_QCI_1_DISCOVERY_INTERVENTIONS",
        "claim_boundary": protocol["claim_boundary"],
    })
    result_path = output_root / "selection.json"
    _write_json(result_path, result)
    manifest = {
        "manifest_version": "1.0.0",
        "experiment_id": result["experiment_id"], "run_id": result["run_id"],
        "utc_timestamp": result["utc_timestamp"], "git_commit": _git("rev-parse", "HEAD"),
        "uncommitted_diff": bool(_git("diff", "--name-only")),
        "dataset_manifest_hashes": {
            "dcap_summary": protocol["dcap_summary_sha256"],
            "dcap_manifest": protocol["dcap_manifest_sha256"],
            "qualification_rows": sha256_file(QUALIFICATION_ROWS),
        },
        "model_id": protocol["model_id"], "model_revision": protocol["model_revision"],
        "tokenizer_revision": protocol["model_revision"], "prompt_versions": {},
        "random_seeds": [42], "hardware": platform.platform(),
        "python_env_hash": "not_applicable_no_model_loaded", "command_line": sys.argv,
        "config_file": str(PROTOCOL_PATH.relative_to(ROOT)), "raw_output_path": str(result_path),
        "artifact_paths": {str(result_path): sha256_file(result_path)},
    }
    _write_json(output_root / "manifest.json", manifest)
    return result


def main() -> None:
    """CLI entry point for frozen QCI-1 selection."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--activations", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    result = run(arguments.activations.resolve(), arguments.output.resolve())
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
