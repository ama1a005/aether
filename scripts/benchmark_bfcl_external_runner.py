"""Self-contained external compute runner for official BFCL evaluation.

Designed for execution on qualified GPU environments (e.g. Kaggle / Slurm / Modal).
Validates pinned package version, model revision, snapshot manifest,
executes generation and evaluation via the disclosed AETHER Qwen2.5 adapter,
and generates verified summary artifacts.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from benchmarks.nov19_bfcl.preflight import (
    PHASE1_CATEGORIES,
    PINNED_MODEL_REVISION,
    PINNED_PACKAGE_VERSION,
    run_bfcl_preflight,
)
from benchmarks.nov19_bfcl.report import assemble_bfcl_summary
from benchmarks.nov19_bfcl.runner import BFCLRunner
from benchmarks.nov19_bfcl.verifier import BFCLArtifactVerifier


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run official BFCL benchmark on qualified GPU compute"
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        required=True,
        help="Path to model snapshot manifest JSON",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/phase1/bfcl/official"),
        help="Output directory for official BFCL artifacts",
    )
    parser.add_argument(
        "--num-gpus",
        type=int,
        default=1,
        help="Number of GPUs to allocate for vLLM",
    )
    parser.add_argument(
        "--backend",
        type=str,
        default="vllm",
        choices=["vllm", "sglang"],
        help="Inference backend",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run preflight and generate plan without model execution",
    )
    args = parser.parse_args()

    runner = BFCLRunner(
        snapshot_manifest=args.manifest,
        output_dir=args.output_dir,
        categories=PHASE1_CATEGORIES,
        package_version=PINNED_PACKAGE_VERSION,
        model_revision=PINNED_MODEL_REVISION,
        backend=args.backend,
        num_gpus=args.num_gpus,
    )

    if args.dry_run:
        print("[BFCL Runner] Executing dry run...")
        plan = runner.dry_run()
        print(json.dumps(plan, indent=2))
        sys.exit(0 if plan["preflight"]["passed"] else 1)

    print("[BFCL Runner] Running preflight checks...")
    preflight = run_bfcl_preflight(
        manifest_path=args.manifest,
        categories=PHASE1_CATEGORIES,
        backend=args.backend,
        num_gpus=args.num_gpus,
        verify_snapshot_hashes=True,
    )

    if not preflight.passed:
        print("[BFCL Runner] Preflight FAILED with reasons:")
        for r in preflight.reasons:
            print(f"  - {r}")
        print("\nPreflight details:")
        print(json.dumps(preflight.details, indent=2))
        sys.exit(1)

    print("[BFCL Runner] Preflight PASSED. Executing official BFCL pipeline...")
    exec_result = runner.execute()
    print(f"[BFCL Runner] Execution complete: {exec_result}")

    print("[BFCL Runner] Verifying generated artifacts independently...")
    verifier = BFCLArtifactVerifier(
        result_dir=args.output_dir,
        expected_categories=PHASE1_CATEGORIES,
    )
    verification = verifier.verify()
    if not verification.passed:
        print("[BFCL Runner] Verification FAILED:")
        for r in verification.reasons:
            print(f"  - {r}")
        sys.exit(2)

    print("[BFCL Runner] Verification PASSED. Writing official summary...")
    summary_path = args.output_dir / "summary.json"
    summary = assemble_bfcl_summary(verification, output_path=summary_path)
    print(f"[BFCL Runner] Summary written to {summary_path}")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
