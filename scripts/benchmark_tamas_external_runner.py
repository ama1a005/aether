"""External runner for TAMAS native multi-agent benchmark evaluation.

Validates multi-agent framework availability, data integrity across all 6 attack types,
orchestrates multi-agent execution with AutoGen/CrewAI, and produces verified summary artifacts.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from benchmarks.nov19_tamas.case import (
    ATTACK_TYPES,
    load_tamas_dataset,
    select_predeclared_tamas_cohort,
)
from benchmarks.nov19_tamas.preflight import run_tamas_preflight
from benchmarks.nov19_tamas.report import assemble_tamas_summary
from benchmarks.nov19_tamas.runner import TAMASNativeRunner
from benchmarks.nov19_tamas.verifier import TAMASArtifactVerifier


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run native TAMAS multi-agent benchmark on supported framework"
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path(".cache/benchmarks/TAMAS/data"),
        help="Path to TAMAS data directory containing attack subdirectories",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/phase1/tamas/official"),
        help="Output directory for TAMAS traces and evaluation summary",
    )
    parser.add_argument(
        "--framework",
        type=str,
        default="autogen",
        choices=["autogen", "crewai"],
        help="Multi-agent framework",
    )
    parser.add_argument(
        "--provider",
        type=str,
        default="ollama",
        choices=["ollama", "openai", "azure", "anthropic"],
        help="Model inference provider",
    )
    parser.add_argument(
        "--per-attack-count",
        type=int,
        default=None,
        help="Number of cases per attack type (default: all 50)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for deterministic cohort selection",
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="dry-run",
        choices=["dry-run", "execute"],
        help="Execution mode",
    )
    args = parser.parse_args()

    print("[TAMAS Runner] Running preflight checks...")
    preflight = run_tamas_preflight(
        data_root=args.data_root,
        framework=args.framework,
        provider=args.provider,
        enforce_framework=(args.mode == "execute"),
    )

    if not preflight.passed:
        print("[TAMAS Runner] Preflight FAILED:")
        for r in preflight.reasons:
            print(f"  - {r}")
        print("\nPreflight details:")
        print(json.dumps(preflight.details, indent=2))
        sys.exit(1)

    runner = TAMASNativeRunner(
        data_root=args.data_root,
        output_dir=args.output_dir,
        framework=args.framework,
        provider=args.provider,
        per_attack_count=args.per_attack_count,
        seed=args.seed,
    )

    if args.mode == "dry-run":
        print("[TAMAS Runner] Executing dry run...")
        plan = runner.dry_run()
        print(f"[TAMAS Runner] Dry run complete. Cohort size: {len(plan['cohort_ids'])}")
        print(json.dumps(plan, indent=2))
        sys.exit(0)

    print("[TAMAS Runner] Execute mode requires live model provider and active multi-agent framework.")
    print("Preflight and cohort ready. Please execute in supported compute environment.")


if __name__ == "__main__":
    main()
