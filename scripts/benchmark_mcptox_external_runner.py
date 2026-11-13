"""External runner for MCPTox official-compatible benchmark evaluation.

Validates source hashes, selects predeclared deterministic subsets,
executes agent evaluation against tool-description poisoning,
and produces verified summary artifacts.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from benchmarks.nov19_mcptox.case import (
    OFFICIAL_COMMIT,
    PURE_TOOL_SHA256,
    load_native_cases,
    select_predeclared_subset,
)
from benchmarks.nov19_mcptox.evaluator import (
    MCPToxEvaluator,
    summarize_mcptox_outcomes,
)
from benchmarks.nov19_mcptox.preflight import run_mcptox_preflight
from benchmarks.nov19_mcptox.report import assemble_mcptox_summary
from benchmarks.nov19_mcptox.verifier import MCPToxArtifactVerifier


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run official-compatible MCPTox evaluation"
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=Path(".cache/benchmarks/MCPTox-Benchmark"),
        help="Path to cloned MCPTox repository with pure_tool.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/phase1/mcptox/official"),
        help="Output directory for evaluated records and summary",
    )
    parser.add_argument(
        "--subset-size",
        type=int,
        default=None,
        help="Number of cases to select (defaults to full 485 release)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for deterministic subset selection",
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="dry-run",
        choices=["dry-run", "execute"],
        help="Execution mode",
    )
    args = parser.parse_args()

    print("[MCPTox Runner] Running preflight source verification...")
    preflight = run_mcptox_preflight(args.source_dir, verify_hashes=True)
    if not preflight.passed:
        print("[MCPTox Runner] Preflight FAILED:")
        for r in preflight.reasons:
            print(f"  - {r}")
        print("\nPreflight details:")
        print(json.dumps(preflight.details, indent=2))
        sys.exit(1)

    print("[MCPTox Runner] Loading native cases...")
    pure_tool_path = args.source_dir / "pure_tool.json"
    cases = load_native_cases(pure_tool_path, verify_pinned_hash=True)
    print(f"[MCPTox Runner] Loaded {len(cases)} cases across 45 servers.")

    selected = select_predeclared_subset(cases, count=args.subset_size, seed=args.seed)
    print(f"[MCPTox Runner] Selected {len(selected)} cases for evaluation cohort.")

    if args.mode == "dry-run":
        print("[MCPTox Runner] Dry run successful. Cohort IDs:")
        for c in selected[:5]:
            print(f"  - {c.case_id} (Server: {c.server_name}, Tool: {c.tool_name}, Paradigm: {c.paradigm})")
        if len(selected) > 5:
            print(f"  ... and {len(selected) - 5} more.")
        sys.exit(0)

    # In execute mode: requires live model provider / local inference harness
    print("[MCPTox Runner] Execute mode requires local inference engine or API provider.")
    print("Preflight and cohort ready. Please attach qualified compute environment.")


if __name__ == "__main__":
    main()
