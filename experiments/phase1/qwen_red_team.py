"""Run an approved development-only red-team campaign against real Qwen A/B."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import platform
from pathlib import Path
import subprocess
import sys

import torch
import yaml

from attacks.corpus.attack_store import AttackStore
from attacks.corpus.builder import CorpusBuilder
from attacks.orchestration import CampaignConfig, run_campaign
from attacks.qwen_backend import QwenRedTeamBackend
from benchmarks.bfcl_qwen25 import verify_snapshot_manifest
from contracts.schemas import PatientCase
from experiments.external_bundle import verify_protocol_approval, write_bundle_manifest
from instrumentation.adapters import Qwen2ModelAdapter


ROOT = Path(__file__).resolve().parents[2]


def run(config_path: Path, approval_path: Path, snapshot_manifest: Path, output: Path) -> Path:
    """Load the pinned snapshot only after protocol and split checks pass."""
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    verify_protocol_approval(config_path, approval_path)
    if config.get("status") != "awaiting_human_protocol_review":
        raise ValueError("unexpected red-team proposal status")
    if config.get("split") != "development" or config.get("validation_executions") != 0 or config.get("test_executions") != 0:
        raise PermissionError("red-team protocol attempts protected-split access")
    if output.exists():
        raise FileExistsError(output)
    revision = str(config["model_revision"])
    snapshot = verify_snapshot_manifest(snapshot_manifest, revision)
    registry = json.loads((ROOT / config["case_registry"]).read_text(encoding="utf-8"))["cases"]
    cases = [PatientCase(str(row["case_id"]), dict(row["features"]), str(row["ground_truth_decision"]),
                         source_dataset=str(row["dataset_version"]), source_split=str(row["split"])) for row in registry]
    if not cases or any(case.source_split != "development" for case in cases):
        raise ValueError("red-team cases must be nonempty and development-only")
    adapter = Qwen2ModelAdapter(str(snapshot), revision, snapshot.parent.parent.parent,
                               dtype=torch.float32, device="cpu", local_files_only=True, low_cpu_mem_usage=True)
    adapter.load()
    adapter.tokenizer.padding_side = "left"
    backend = QwenRedTeamBackend(adapter, model_id=str(config["model_id"]), model_revision=revision)
    store = AttackStore(str(output.parent / f".{output.name}-corpus"))
    attacks = CorpusBuilder(int(config["seed"])).build_phase1_corpus(store, int(config["n_per_family"]))
    campaign = CampaignConfig(str(config["experiment_id"]), int(config["seed"]),
                              int(config["max_target_calls"]), "development")
    summary = run_campaign(backend, cases, attacks, campaign, output)
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    freeze = subprocess.run([sys.executable, "-m", "pip", "freeze", "--all"], check=True,
                            capture_output=True, text=True).stdout
    write_bundle_manifest(output, {
        "experiment_id": config["experiment_id"], "run_id": output.name,
        "utc_timestamp": datetime.now(timezone.utc).isoformat(), "git_commit": manifest["git_commit"],
        "uncommitted_diff": manifest["uncommitted_diff"], "dataset_manifest_hashes": manifest["dataset_manifest_hashes"],
        "model_id": config["model_id"], "model_revision": revision, "tokenizer_revision": revision,
        "random_seeds": [int(config["seed"])], "hardware": platform.platform(),
        "python_env_hash": hashlib.sha256(freeze.encode()).hexdigest(), "command_line": sys.argv,
        "config_file": str(config_path), "evidence_kind": "qwen_red_team",
        "validation_executions": 0, "test_executions": 0,
    })
    if summary["target_calls"] > campaign.max_target_calls:
        raise RuntimeError("red-team target-call budget overrun")
    return output / "bundle_manifest.json"


def main() -> None:
    """Execute the approved real-Qwen campaign."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--approval", type=Path, required=True)
    parser.add_argument("--snapshot-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    print(run(arguments.config, arguments.approval, arguments.snapshot_manifest, arguments.output))


if __name__ == "__main__":
    main()
