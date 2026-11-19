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
from attacks.corpus.provenance import generate_provenance_manifest
from attacks.orchestration import CampaignConfig, run_campaign
from attacks.qwen_backend import QwenRedTeamBackend
from benchmarks.bfcl_qwen25 import verify_snapshot_manifest
from contracts.schemas import PatientCase
from experiments.external_bundle import verify_protocol_approval, write_bundle_manifest
from experiments.manifest import environment_inventory, sha256_file
from instrumentation.adapters import Qwen2ModelAdapter


ROOT = Path(__file__).resolve().parents[2]


def preflight(config_path: Path, approval_path: Path, snapshot_manifest: Path | None, output: Path, *, resume: bool = False) -> dict[str, object]:
    """Run every model-free admission gate before a Qwen snapshot is accessed."""
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    required = {"case_selection_policy", "attack_families", "attack_surfaces", "corpus_generation_policy",
                "eligibility_rule", "attempt_accounting", "checkpoint_policy", "raw_output_schema", "metrics"}
    missing = sorted(key for key in required if not config.get(key))
    if missing:
        raise ValueError(f"red-team proposal is incomplete: {missing}")
    verify_protocol_approval(config_path, approval_path)
    if config.get("status") != "awaiting_human_protocol_review":
        raise ValueError("unexpected red-team proposal status")
    if config.get("split") != "development" or config.get("validation_executions") != 0 or config.get("test_executions") != 0:
        raise PermissionError("red-team protocol attempts protected-split access")
    if output.exists() and not resume:
        raise FileExistsError(output)
    if resume and not (output / "plan.json").is_file():
        raise FileNotFoundError("resume requires an existing canonical campaign plan")
    revision = str(config["model_revision"])
    snapshot = verify_snapshot_manifest(snapshot_manifest, revision) if snapshot_manifest is not None else None
    registry = json.loads((ROOT / config["case_registry"]).read_text(encoding="utf-8"))["cases"]
    development_rows = [row for row in registry if row.get("split") == "development"]
    cases = [PatientCase(str(row["case_id"]), dict(row["features"]), str(row["ground_truth_decision"]),
                         source_dataset=str(row["dataset_version"]), source_split=str(row["split"]))
             for row in development_rows]
    if not cases or any(case.source_split != "development" for case in cases):
        raise ValueError("red-team cases must be nonempty and development-only")
    status = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, check=True, capture_output=True, text=True)
    if status.stdout.strip():
        raise ValueError("real-Qwen preflight requires a clean source checkout")
    store = AttackStore(str(output.parent / f".{output.name}-corpus"))
    attacks = CorpusBuilder(int(config["seed"])).build_phase1_corpus(store, int(config["n_per_family"]))
    corpus_provenance = generate_provenance_manifest(str(store.corpus_dir), int(config["seed"]),
        sorted({attack.family for attack in attacks}))
    corpus_provenance.update({"selected_ids": [attack.attack_id for attack in attacks],
        "family_counts": {family: sum(attack.family == family for attack in attacks) for family in sorted({attack.family for attack in attacks})},
        "selection_policy": "CorpusBuilder.build_phase1_corpus"})
    return {"config": config, "snapshot": snapshot, "cases": cases, "revision": revision,
            "attacks": attacks, "corpus_provenance": corpus_provenance}


def run(config_path: Path, approval_path: Path, snapshot_manifest: Path, output: Path, *, resume: bool = False) -> Path:
    """Load Qwen only after the approved model-free preflight succeeds."""
    gate = preflight(config_path, approval_path, snapshot_manifest, output, resume=resume)
    config, snapshot, cases, revision = gate["config"], gate["snapshot"], gate["cases"], gate["revision"]
    attacks, corpus_provenance = gate["attacks"], gate["corpus_provenance"]
    if snapshot is None:
        raise ValueError("a verified snapshot manifest is required before model loading")
    adapter = Qwen2ModelAdapter(str(snapshot), revision, snapshot.parent.parent.parent,
                               dtype=torch.float32, device="cpu", local_files_only=True, low_cpu_mem_usage=True)
    adapter.load()
    adapter.tokenizer.padding_side = "left"
    backend = QwenRedTeamBackend(adapter, model_id=str(config["model_id"]), model_revision=revision)
    campaign = CampaignConfig(str(config["experiment_id"]), int(config["seed"]),
                              int(config["max_target_calls"]), "development")
    summary = run_campaign(backend, cases, attacks, campaign, output, resume=resume,
                           corpus_provenance=corpus_provenance)
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    campaign_summary = output / "campaign_summary.json"
    (output / "summary.json").replace(campaign_summary)
    completion = {
        "overall": "EXECUTION_COMPLETE_UNVERIFIED", "model_id": config["model_id"], "model_revision": revision,
        "evidence_class": "real_qwen_development_red_team", "campaign": summary,
        "validation_executions": 0, "test_executions": 0,
    }
    summary_path = output / "summary.json"
    summary_path.write_text(json.dumps(completion, indent=2, allow_nan=False), encoding="utf-8")
    manifest["artifact_paths"] = {
        **{key: value for key, value in manifest["artifact_paths"].items()
           if not str(key).endswith("summary.json")},
        str(campaign_summary): sha256_file(campaign_summary), str(summary_path): sha256_file(summary_path),
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    freeze = environment_inventory(ROOT)
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
    parser.add_argument("--snapshot-manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--resume", action="store_true")
    arguments = parser.parse_args()
    if arguments.preflight_only:
        print(json.dumps(preflight(arguments.config, arguments.approval, arguments.snapshot_manifest, arguments.output,
                                   resume=arguments.resume), default=str, indent=2))
    else:
        if arguments.snapshot_manifest is None:
            parser.error("--snapshot-manifest is required unless --preflight-only is used")
        print(run(arguments.config, arguments.approval, arguments.snapshot_manifest, arguments.output, resume=arguments.resume))


if __name__ == "__main__":
    main()
