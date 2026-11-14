"""Run the frozen qualification task for a separately reviewed second model."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

from experiments.manifest import sha256_file

from paired_trace import run_model_qualification as primary


ROOT = Path(__file__).resolve().parents[1]


def prepare(candidate_config: Path, output: Path) -> tuple[dict, Path]:
    """Validate a reviewed candidate and derive the unchanged hardware gate."""
    candidate_config = candidate_config.resolve()
    try:
        candidate_config.relative_to(ROOT)
    except ValueError as error:
        raise ValueError("second-model config must be committed inside the repository") from error
    config = json.loads(candidate_config.read_text(encoding="utf-8"))
    required = {
        "status": "frozen_for_authorized_campaign", "device": "cpu", "dtype": "float32",
        "quantized": False, "explicit_offload": False, "disk_offload": False,
        "low_cpu_mem_usage": True, "trust_remote_code": False, "local_files_only": True,
    }
    failures = [key for key, value in required.items() if config.get(key) != value]
    if failures or not isinstance(config.get("model_id"), str) or re.fullmatch(r"[0-9a-f]{40}", str(config.get("revision", ""))) is None:
        raise ValueError(f"second-model candidate is not prospectively frozen: {failures}")
    if config["model_id"] == "Qwen/Qwen2.5-1.5B-Instruct":
        raise ValueError("second-model qualification requires a distinct model identity")
    approval = config.get("human_review")
    if not isinstance(approval, dict) or approval.get("approved") is not True or not approval.get("reviewer"):
        raise ValueError("second-model candidate lacks explicit human review")
    gate = json.loads(primary.HW_PATH.read_text(encoding="utf-8"))
    gate["candidate_model_id"] = config["model_id"]
    output.mkdir(parents=True, exist_ok=True)
    derived = output / "secondary_mq_hw1.json"
    derived.write_text(json.dumps(gate, indent=2, sort_keys=True), encoding="utf-8")
    return config, derived


def main() -> None:
    """Delegate to the tested qualification engine with secondary identities."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cache", type=Path)
    parser.add_argument("--preflight-only", action="store_true")
    arguments = parser.parse_args()
    config, hardware = prepare(arguments.candidate_config, arguments.output)
    primary.MODEL_CONFIG_PATH = arguments.candidate_config.resolve()
    primary.HW_PATH = hardware
    primary.EXPERIMENT_ID = "P0_target_secondary_model_qualification"
    primary.RUN_ID = "P0_target_secondary_model_qualification_seed42"
    delegated = [sys.argv[0], "--output", str(arguments.output)]
    if arguments.cache:
        delegated.extend(("--cache", str(arguments.cache)))
    if arguments.preflight_only:
        delegated.append("--preflight-only")
    sys.argv = delegated
    primary.main()
    if not arguments.preflight_only:
        summary_path = arguments.output / "summary.json"
        manifest_path = arguments.output / "manifest.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        if summary.get("mq_g1", {}).get("overall") != "PASS" or summary.get("mq_g2", {}).get("overall") != "PASS":
            raise RuntimeError("second model did not pass both frozen qualification gates")
        summary["overall"] = "PASS"
        summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for key in list(manifest["artifact_paths"]):
            if str(key).endswith("summary.json"):
                manifest["artifact_paths"][key] = sha256_file(summary_path)
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    main()
