"""Execute pinned BFCL or AgentDojo plans and retain an admissible raw bundle."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from importlib.metadata import PackageNotFoundError, version
import json
import platform
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping

import yaml

from benchmarks.native_runners import NativeBenchmarkPlan, agentdojo_plan, bfcl_qwen25_plan, execute_native_plan
from benchmarks.nov19_bfcl.preflight import (
    ADAPTER_REGISTRY_NAME,
    PHASE1_CATEGORIES,
    PINNED_MODEL_ID,
    PINNED_MODEL_REVISION,
    PINNED_PACKAGE,
    PINNED_PACKAGE_VERSION,
    PINNED_WHEEL_SHA256,
    run_bfcl_preflight,
)
from benchmarks.nov19_bfcl.report import assemble_bfcl_summary
from benchmarks.nov19_bfcl.verifier import BFCLArtifactVerifier, VerificationResult
from experiments.external_bundle import (
    artifact_hashes,
    runtime_metadata,
    sha256_file,
    write_bundle_manifest,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs/benchmarks/phase1_external.yaml"
DEFAULT_BFCL_APPROVAL = ROOT / "results/phase1/protocol_approvals/bfcl_official.json"
BFCL_CONFIG_SHA256 = "017bce07725a36ed4f7d8f08b399a22c1b4092271c2ce2473b2fd138b5e4ff75"


def build_plan(benchmark: str, config_path: Path, output: Path,
               snapshot_manifest: Path | None, *, num_gpus: int = 1,
               backend: str = "vllm") -> NativeBenchmarkPlan:
    """Build one pinned official-package plan without executing it."""
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if config.get("schema_version") != 1 or config.get("split") != "development":
        raise ValueError("official benchmark config must be schema 1 development preparation")
    if benchmark == "bfcl":
        if snapshot_manifest is None or not snapshot_manifest.is_file():
            raise FileNotFoundError("BFCL requires the qualified model snapshot manifest")
        item = config["bfcl"]
        return bfcl_qwen25_plan(
            package_version=str(item["package_version"]), model_revision=str(item["model_revision"]),
            snapshot_manifest=snapshot_manifest, categories=item["categories"], output_dir=output / "official_raw",
            num_gpus=num_gpus, backend=backend,
        )
    if benchmark == "agentdojo":
        item = config["agentdojo"]
        return agentdojo_plan(
            package_version=str(item["package_version"]), suite=str(item["suite"]), model=str(item["model"]),
            benchmark_version=str(item["benchmark_version"]), output_dir=output / "official_raw",
            user_tasks=item["user_tasks"], injection_tasks=item["injection_tasks"],
        )
    raise ValueError(f"unsupported official benchmark: {benchmark}")


def _command(command: list[str]) -> str:
    return subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()


def _load_config(config_path: Path, benchmark: str) -> dict[str, Any]:
    """Load a development config and enforce the frozen BFCL profile."""
    resolved = config_path.resolve()
    if resolved != DEFAULT_CONFIG.resolve():
        raise ValueError("official execution only accepts the repository's canonical config")
    if sha256_file(resolved) != BFCL_CONFIG_SHA256:
        raise ValueError("official benchmark configuration hash differs from the reviewed config")
    config = yaml.safe_load(resolved.read_text(encoding="utf-8"))
    if not isinstance(config, dict) or config.get("schema_version") != 1 or config.get("split") != "development":
        raise ValueError("official benchmark config must be schema 1 development preparation")
    if benchmark == "bfcl":
        item = config.get("bfcl", {})
        expected = {
            "package": PINNED_PACKAGE,
            "package_version": PINNED_PACKAGE_VERSION,
            "package_wheel_sha256": PINNED_WHEEL_SHA256,
            "model": PINNED_MODEL_ID,
            "model_revision": PINNED_MODEL_REVISION,
            "registry_adapter": ADAPTER_REGISTRY_NAME,
            "protocol_label": "official_evaluator_with_disclosed_aether_model_adapter",
            "categories": list(PHASE1_CATEGORIES),
            "partial_evaluation": False,
        }
        mismatches = [key for key, value in expected.items() if item.get(key) != value]
        if mismatches:
            raise ValueError(f"frozen BFCL configuration differs in fields: {mismatches}")
    return config


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    """Write a complete JSON artifact to a new path."""
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


def _make_bfcl_metadata(config_path: Path, snapshot_manifest: Path,
                        package_wheel: Path, output: Path) -> dict[str, Any]:
    """Capture the clean source and pinned BFCL inputs before output creation."""
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))["bfcl"]
    metadata = runtime_metadata(
        repository=ROOT,
        experiment_id=f"P0_target_{datetime.now(timezone.utc):%Y%m%d}_bfcl_official_0",
        run_id=f"bfcl-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}",
        dataset_manifest_hashes={
            "benchmark_config": sha256_file(config_path),
            "model_snapshot_manifest": sha256_file(snapshot_manifest),
            "bfcl_package_wheel": sha256_file(package_wheel),
        },
        model_id=config["model"],
        model_revision=config["model_revision"],
        tokenizer_revision=config["model_revision"],
        seeds=[0],
        config_file=config_path,
        evidence_kind="bfcl_official",
    )
    try:
        backend_version = version("vllm")
    except PackageNotFoundError:
        backend_version = None
    import torch

    metadata.update({
        "raw_output_path": str((output / "official_raw").resolve()),
        "prompt_versions": {"bfcl_adapter": ADAPTER_REGISTRY_NAME},
        "package_wheel_sha256": sha256_file(package_wheel),
        "protocol_label": config["protocol_label"],
        "inference_backend": "vllm",
        "inference_backend_version": backend_version,
        "torch_version": torch.__version__,
        "cuda_runtime_version": torch.version.cuda,
    })
    return metadata


def _finalize_bfcl_bundle(output: Path, metadata: dict[str, Any]) -> Path:
    """Write audit inventory and the independently verifiable bundle manifest."""
    _write_json(output / "manifest.json", metadata)
    current = artifact_hashes(output, exclude=("bundle_manifest.json", "archive_contents.json"))
    _write_json(output / "archive_contents.json", {
        "schema_version": "aether.bfcl-archive-inventory.v1",
        "artifacts": current,
        "claim_boundary": "Hash inventory only; scientific status is in summary.json.",
    })
    return write_bundle_manifest(output, metadata)


def _blocked_summary(reasons: list[str]) -> dict[str, Any]:
    """Create a blocked readiness report without implying benchmark execution."""
    summary = assemble_bfcl_summary(
        VerificationResult(False, tuple(reasons), {}, {}),
        execution_blocked_reasons=reasons,
    )
    hardware_preflight = preflight.details.get("hardware", {})
    summary.update({
        "execution_status": "BLOCKED_BEFORE_MODEL_ACCESS",
        "subset_totals": None,
        "invalid_error_counts": None,
        "validation_executions": 0,
        "test_executions": 0,
    })
    return summary


def run(benchmark: str, config_path: Path, output: Path,
        snapshot_manifest: Path | None, *, package_wheel: Path | None = None,
        backend: str = "vllm", num_gpus: int = 1,
        approval_path: Path = DEFAULT_BFCL_APPROVAL) -> Path:
    """Execute an official plan and retain native outputs plus a verified bundle."""
    if output.exists():
        raise FileExistsError(f"output already exists: {output}")
    resolved_output = output.resolve()
    if resolved_output == ROOT.resolve() or ROOT.resolve() in resolved_output.parents:
        raise ValueError("external benchmark artifacts must be written outside the Git checkout")
    if _command(["git", "status", "--porcelain"]):
        raise RuntimeError("official evidence execution requires a clean source tree")
    config = _load_config(config_path, benchmark)
    if benchmark == "bfcl":
        if backend != "vllm":
            raise ValueError("the frozen BFCL profile requires the pinned vLLM backend")
        # Require a separate human decision over the exact frozen configuration
        # before loading the model snapshot or invoking any evaluator command.
        from experiments.external_bundle import verify_protocol_approval
        verify_protocol_approval(config_path, approval_path)
    if benchmark != "bfcl":
        plan = build_plan(benchmark, config_path, output, snapshot_manifest)
        output.mkdir(parents=True)
        records = execute_native_plan(plan, output / "command_records")
        item = config[benchmark]
        summary = {
            "schema_version": "aether.official-benchmark-summary.v1", "overall": "PASS",
            "benchmark": benchmark, "official_evaluator": True,
            "model_id": item["model"], "result_scope": plan.result_scope,
            "command_count": len(records), "all_commands_passed": True,
            "validation_executions": 0, "test_executions": 0,
        }
        (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        freeze = _command([sys.executable, "-m", "pip", "freeze", "--all"])
        metadata = {
            "experiment_id": f"P0_{benchmark}_{datetime.now(timezone.utc):%Y%m%d}_official_0",
            "run_id": f"{benchmark}-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}",
            "utc_timestamp": datetime.now(timezone.utc).isoformat(), "git_commit": _command(["git", "rev-parse", "HEAD"]),
            "uncommitted_diff": False, "dataset_manifest_hashes": {"config": sha256_file(config_path)},
            "model_id": item["model"], "model_revision": str(item.get("model_revision", "official_runtime_managed")),
            "tokenizer_revision": str(item.get("model_revision", "official_runtime_managed")),
            "random_seeds": [0], "hardware": platform.platform(),
            "python_env_hash": hashlib.sha256(freeze.encode()).hexdigest(), "command_line": sys.argv,
            "config_file": str(config_path), "evidence_kind": f"{benchmark}_official",
            "validation_executions": 0, "test_executions": 0,
        }
        return write_bundle_manifest(output, metadata)

    item = config["bfcl"]
    if snapshot_manifest is None or not snapshot_manifest.is_file():
        raise FileNotFoundError("BFCL requires the frozen Qwen snapshot manifest")
    if package_wheel is None or not package_wheel.is_file():
        raise FileNotFoundError("BFCL requires the pinned official package wheel for hash verification")
    if num_gpus < 1:
        raise ValueError("BFCL GPU count must be positive")
    plan = build_plan(benchmark, config_path, output, snapshot_manifest,
                      num_gpus=num_gpus, backend=backend)
    metadata = _make_bfcl_metadata(config_path, snapshot_manifest, package_wheel, output)
    preflight = run_bfcl_preflight(
        manifest_path=snapshot_manifest,
        categories=item["categories"],
        backend=backend,
        num_gpus=num_gpus,
        wheel_path=package_wheel,
        verify_snapshot_hashes=True,
    )
    output.mkdir(parents=True)
    _write_json(output / "preflight.json", preflight.to_dict())
    if not preflight.passed:
        _write_json(output / "summary.json", _blocked_summary(list(preflight.reasons)))
        _finalize_bfcl_bundle(output, metadata)
        return output / "summary.json"

    execution_error: str | None = None
    try:
        records = execute_native_plan(plan, output / "command_records")
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        records = ()
        execution_error = f"{type(exc).__name__}: {exc}"

    if execution_error:
        verification = VerificationResult(False, (execution_error,), {}, {})
    else:
        verification = BFCLArtifactVerifier(
            Path(plan.output_dir), expected_categories=PHASE1_CATEGORIES,
            expected_model_adapter=ADAPTER_REGISTRY_NAME,
        ).verify()
    summary = assemble_bfcl_summary(verification)
    summary.update({
        "execution_status": "COMPLETE" if not execution_error else "FAILED",
        "official_evaluator": verification.passed and execution_error is None,
        "official_evaluator_executed": bool(records) and execution_error is None,
        "custom_model_adapter_disclosed": True,
        "inference_backend": "vllm",
        "inference_backend_version": hardware_preflight.get("backend_version"),
        "torch_version": hardware_preflight.get("torch_version"),
        "cuda_runtime_version": hardware_preflight.get("cuda_runtime_version"),
        "model_id": PINNED_MODEL_ID,
        "model_revision": PINNED_MODEL_REVISION,
        "tokenizer_revision": PINNED_MODEL_REVISION,
        "package_wheel_sha256": PINNED_WHEEL_SHA256,
        "subset_totals": verification.metrics.get("categories", {}),
        "invalid_error_counts": {
            "invalid": verification.metrics.get("total_errors"),
            "errors": verification.metrics.get("total_errors"),
        },
        "validation_executions": 0,
        "test_executions": 0,
    })
    if execution_error:
        summary["execution_error"] = execution_error
    _write_json(output / "summary.json", summary)
    metadata["raw_output_path"] = str(Path(plan.output_dir).resolve())
    _finalize_bfcl_bundle(output, metadata)
    return output / "summary.json"


def main() -> None:
    """Run a selected pinned native benchmark."""
    parser = argparse.ArgumentParser()
    parser.add_argument("benchmark", choices=("bfcl", "agentdojo"))
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--snapshot-manifest", type=Path)
    parser.add_argument("--package-wheel", type=Path,
                        help="Downloaded bfcl_eval wheel whose pinned SHA-256 was reviewed")
    parser.add_argument("--backend", choices=("vllm",), default="vllm")
    parser.add_argument("--num-gpus", type=int, default=1)
    parser.add_argument("--approval", type=Path, default=DEFAULT_BFCL_APPROVAL,
                        help="Human approval JSON bound to the exact canonical BFCL config")
    arguments = parser.parse_args()
    result = run(
        arguments.benchmark, arguments.config, arguments.output,
        arguments.snapshot_manifest, package_wheel=arguments.package_wheel,
        backend=arguments.backend, num_gpus=arguments.num_gpus,
        approval_path=arguments.approval,
    )
    print(result)


if __name__ == "__main__":
    main()
