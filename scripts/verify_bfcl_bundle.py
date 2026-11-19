"""Independently verify the native BFCL outputs and AETHER evidence bundle."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

from benchmarks.nov19_bfcl.preflight import (
    ADAPTER_REGISTRY_NAME,
    PHASE1_CATEGORIES,
    PINNED_MODEL_ID,
    PINNED_MODEL_REVISION,
    PINNED_PACKAGE_VERSION,
    PINNED_WHEEL_SHA256,
    PINNED_BACKEND_VERSION,
    PINNED_TORCH_VERSION,
    PINNED_CUDA_VERSION,
)
from benchmarks.nov19_bfcl.verifier import BFCLArtifactVerifier
from experiments.external_bundle import artifact_hashes, verify_bundle


def verify(root: Path) -> dict[str, Any]:
    """Verify bundle hashes, official command records, BFCL rows and summary."""
    root = Path(root).resolve()
    bundle = verify_bundle(root, expected_kind="bfcl_official")
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    summary = json.loads((root / "summary.json").read_text(encoding="utf-8"))
    preflight = json.loads((root / "preflight.json").read_text(encoding="utf-8"))
    inventory = json.loads((root / "archive_contents.json").read_text(encoding="utf-8"))

    if manifest.get("uncommitted_diff") is not False:
        raise ValueError("BFCL source commit must be clean")
    if manifest.get("model_id") != PINNED_MODEL_ID:
        raise ValueError("BFCL manifest model ID differs from the frozen target")
    if manifest.get("model_revision") != PINNED_MODEL_REVISION:
        raise ValueError("BFCL manifest model revision differs from the frozen target")
    if manifest.get("tokenizer_revision") != PINNED_MODEL_REVISION:
        raise ValueError("BFCL manifest tokenizer revision differs from the frozen target")
    if manifest.get("package_wheel_sha256") != PINNED_WHEEL_SHA256:
        raise ValueError("BFCL manifest package wheel hash differs from the frozen release")
    if manifest.get("protocol_label") != "official_evaluator_with_disclosed_aether_model_adapter":
        raise ValueError("BFCL adapter claim label is absent or incorrect")
    if (manifest.get("inference_backend") != "vllm"
            or manifest.get("inference_backend_version") != PINNED_BACKEND_VERSION
            or manifest.get("torch_version") != PINNED_TORCH_VERSION
            or manifest.get("cuda_runtime_version") != PINNED_CUDA_VERSION):
        raise ValueError("BFCL inference backend or CUDA compatibility pins differ from the frozen runtime")
    required_metadata = {
        "run_id", "utc_timestamp", "git_commit", "uncommitted_diff",
        "dataset_manifest_hashes", "model_id", "model_revision", "tokenizer_revision",
        "prompt_versions", "random_seeds", "hardware", "python_env_hash",
        "command_line", "config_file", "raw_output_path",
    }
    if not required_metadata <= set(manifest):
        raise ValueError(f"BFCL manifest lacks fields: {sorted(required_metadata - set(manifest))}")

    if preflight.get("passed") is not True:
        raise ValueError("BFCL preflight did not pass")
    if summary.get("overall") != "PASS" or summary.get("execution_status") != "COMPLETE":
        raise ValueError("BFCL summary does not describe a verified complete execution")
    if summary.get("official_evaluator") is not True or summary.get("official_evaluator_executed") is not True:
        raise ValueError("BFCL official evaluator execution is not established")
    if summary.get("custom_model_adapter_disclosed") is not True:
        raise ValueError("BFCL summary does not disclose its AETHER model adapter")
    if summary.get("model_id") != PINNED_MODEL_ID or summary.get("model_revision") != PINNED_MODEL_REVISION:
        raise ValueError("BFCL summary model identity differs from the frozen target")
    summary_torch_version = summary.get("torch_version")
    if (summary.get("inference_backend") != "vllm"
            or summary.get("inference_backend_version") != PINNED_BACKEND_VERSION
            or not isinstance(summary_torch_version, str)
            or summary_torch_version.split("+", maxsplit=1)[0] != PINNED_TORCH_VERSION
            or summary.get("cuda_runtime_version") != PINNED_CUDA_VERSION):
        raise ValueError("BFCL summary inference stack differs from the frozen runtime")
    if summary.get("categories") != list(PHASE1_CATEGORIES) or summary.get("partial_evaluation") is not False:
        raise ValueError("BFCL summary categories or complete-evaluation label differ")
    if summary.get("validation_executions") != 0 or summary.get("test_executions") != 0:
        raise ValueError("BFCL bundle records protected-split access")

    command_dir = root / "command_records"
    plan = json.loads((command_dir / "plan.json").read_text(encoding="utf-8"))
    records = [json.loads((command_dir / f"command_{index}.json").read_text(encoding="utf-8"))
               for index in range(2)]
    if len(plan.get("commands", [])) != 2 or [record.get("index") for record in records] != [0, 1]:
        raise ValueError("BFCL raw command record set is incomplete")
    if any(record.get("exit_code") != 0 for record in records):
        raise ValueError("BFCL generation or evaluation command failed")
    expected_categories = ",".join(PHASE1_CATEGORIES)
    for index, verb in enumerate(("generate", "evaluate")):
        command = records[index].get("command", [])
        if verb not in command or ADAPTER_REGISTRY_NAME not in command or expected_categories not in command:
            raise ValueError(f"BFCL command {index} is not the frozen native {verb} invocation")
        if "--model-revision" not in command or PINNED_MODEL_REVISION not in command:
            raise ValueError(f"BFCL command {index} lacks the frozen model revision")

    verification = BFCLArtifactVerifier(
        root / "official_raw", expected_categories=PHASE1_CATEGORIES,
        expected_model_adapter=ADAPTER_REGISTRY_NAME,
    ).verify()
    if not verification.passed:
        raise ValueError(f"BFCL raw output verification failed: {list(verification.reasons)}")
    if summary.get("metrics") != verification.metrics:
        raise ValueError("BFCL summary metrics differ from independently counted raw outputs")
    if summary.get("subset_totals") != verification.metrics.get("categories"):
        raise ValueError("BFCL summary subset totals differ from raw category counts")
    expected_error_count = verification.metrics.get("total_errors")
    if summary.get("invalid_error_counts", {}).get("errors") != expected_error_count:
        raise ValueError("BFCL invalid/error counts differ from raw output rows")

    expected_inventory = artifact_hashes(
        root, exclude=("bundle_manifest.json", "archive_contents.json")
    )
    if inventory.get("artifacts") != expected_inventory:
        raise ValueError("BFCL archive inventory does not match retained artifacts")
    return {
        "verified": True,
        "experiment_id": bundle.experiment_id,
        "run_id": bundle.run_id,
        "artifact_count": bundle.artifact_count,
        "metrics": verification.metrics,
        "claim_boundary": "Official BFCL evaluator with disclosed AETHER adapter; benign competence only.",
    }


def main() -> None:
    """Verify and print one retained BFCL bundle."""
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    arguments = parser.parse_args()
    print(json.dumps(verify(arguments.root), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
