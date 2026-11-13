"""Unified benchmark report builder for paper tables, summaries, and methodology disclosure."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from benchmarks.nov19_reporting.schema import ExternalBenchmarkHandoff, SCHEMA_VERSION
from benchmarks.nov19_reporting.statistics import calculate_binomial_confidence_interval


class UnifiedBenchmarkReportBuilder:
    """Combines verified benchmark results into paper-ready tables and methodology narratives."""

    def __init__(self) -> None:
        self.benchmarks: dict[str, ExternalBenchmarkHandoff] = {}

    def add_benchmark(self, handoff: ExternalBenchmarkHandoff) -> None:
        """Register a verified benchmark handoff."""
        self.benchmarks[handoff.benchmark] = handoff

    def build_summary(self) -> dict[str, Any]:
        """Produce the unified JSON summary spanning all three external benchmarks."""
        results: dict[str, Any] = {}
        for name, handoff in self.benchmarks.items():
            data = handoff.to_dict()
            # Calculate Wilson 95% CI if successes and total/eligible exist
            denom = handoff.denominators
            eligible = denom.get("eligible", denom.get("total_cases", 0))
            successes = denom.get("successes", 0)
            if eligible > 0:
                low, high = calculate_binomial_confidence_interval(successes, eligible)
                data["confidence_interval_95"] = {
                    "method": "wilson",
                    "lower": round(low, 4),
                    "upper": round(high, 4),
                }
            results[name] = data

        return {
            "schema_version": SCHEMA_VERSION,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "claim_boundary": (
                "External benchmarks validate benign tool-calling competence (BFCL), "
                "metadata poisoning susceptibility (MCPTox), and multi-agent adversarial "
                "behavior (TAMAS). They do NOT replace or alone prove AETHER cross-agent "
                "DCMG internal causal circuit discovery or Bridge Verification Protocol novelty."
            ),
            "benchmarks": results,
        }

    def export_csv_table(self, output_path: Path) -> None:
        """Export compact paper-ready CSV table."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        rows = []
        for name, h in self.benchmarks.items():
            denom = h.denominators
            eligible = denom.get("eligible", denom.get("total_cases", 0))
            errors = denom.get("errors", denom.get("error_cases", 0))
            successes = denom.get("successes", 0)
            rate = successes / eligible if eligible > 0 else 0.0

            ci_str = "N/A"
            if eligible > 0:
                low, high = calculate_binomial_confidence_interval(successes, eligible)
                ci_str = f"[{low:.3f}, {high:.3f}]"

            rows.append({
                "Benchmark": name,
                "Evaluation Task": (
                    "Benign Tool Competence" if name == "BFCL"
                    else "Tool Description Poisoning" if name == "MCPTox"
                    else "Multi-Agent Adversarial Robustness"
                ),
                "Evidence Class": h.evidence_class,
                "Status": h.status,
                "Eligible Denominator": eligible,
                "Errors / Invalid": errors,
                "Success Rate / Accuracy": f"{rate:.4f}" if eligible > 0 else "N/A",
                "95% CI (Wilson)": ci_str,
                "Upstream Revision": h.upstream_revision,
            })

        fieldnames = [
            "Benchmark", "Evaluation Task", "Evidence Class", "Status",
            "Eligible Denominator", "Errors / Invalid", "Success Rate / Accuracy",
            "95% CI (Wilson)", "Upstream Revision",
        ]
        with output_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def generate_methodology_paragraph(self) -> str:
        """Produce exact paper methodology paragraph defining validation boundaries."""
        return (
            "### External Benchmark Evaluation Methodology\n\n"
            "To evaluate the behavioral competence and external security robustness of target agent "
            "configurations independent of AETHER's internal mechanistic causal machinery, we evaluated "
            "three standard external protocols: (1) **Berkeley Function Calling Leaderboard (BFCL)** "
            "using official package `bfcl_eval==2026.3.23` across simple, multiple, parallel, and "
            "irrelevance categories under a disclosed model adapter (`AETHER/Qwen2.5-1.5B-Instruct-FC`), "
            "establishing benign tool-calling competence before adversarial manipulation; "
            "(2) **MCPTox** (Wang et al., AAAI 2026, pinned commit `f85189f9`), assessing tool-description "
            "metadata poisoning across 45 servers and 485 poisoned tools under official label accounting "
            "(excluding unparseable `None` responses from the scored denominator); and (3) **TAMAS** "
            "(Microsoft, pinned commit `545c112a`), benchmarking multi-agent conversational vulnerability "
            "across 300 instances spanning Byzantine, Colluding, Contradicting, DPI, Impersonation, and IPI "
            "attack paradigms on native agent frameworks.\n\n"
            "**Scientific Boundary Disclosure:** These external behavioral evaluations establish baseline "
            "model competence and susceptibility to external tool and multi-agent manipulation. They do not "
            "alone establish the causal validity of Distributed Causal Mechanism Graphs (DCMG), cross-agent "
            "activation patching, or targeted circuit remediation, which are evaluated strictly through the "
            "Bridge Verification Protocol (BVP) and locked test splits."
        )
