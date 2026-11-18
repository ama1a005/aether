"""Generate a verified report for the completed AETHER causal core."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from scripts.phase1_execution_status import execution_status
from scripts.verify_core03_remediation_bundle import verify as verify_core03
from scripts.verify_core04_validation_bundle import verify as verify_core04
from scripts.verify_core05_test_bundle import verify as verify_core05
from scripts.verify_qci2_matched_search_bundle import verify as verify_core02


ROOT = Path(__file__).resolve().parents[1]
STAGES = {
    "development_audit": (ROOT / "results/phase1/remediation", "mechanism_receiver_l20_h5", "no_defense", verify_core03),
    "locked_validation": (ROOT / "results/phase1/locked_validation", "frozen_receiver_l20_h5", "no_defense", verify_core04),
    "once_only_test": (ROOT / "results/phase1/once_only_test", "frozen_receiver_l20_h5", "no_defense", verify_core05),
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def wilson(successes: int, total: int, z: float = 1.959963984540054) -> list[float]:
    """Return a two-sided Wilson interval for one binomial proportion."""
    if total <= 0 or not 0 <= successes <= total:
        raise ValueError("Wilson inputs must satisfy 0 <= successes <= total")
    proportion = successes / total; denominator = 1 + z * z / total
    centre = (proportion + z * z / (2 * total)) / denominator
    radius = z * math.sqrt(proportion * (1 - proportion) / total + z * z / (4 * total * total)) / denominator
    return [max(0.0, centre - radius), min(1.0, centre + radius)]


def exact_mcnemar(discordant_baseline_only: int, discordant_repair_only: int) -> float:
    """Return the exact two-sided McNemar/binomial p-value."""
    n = discordant_baseline_only + discordant_repair_only
    if n == 0:
        return 1.0
    k = min(discordant_baseline_only, discordant_repair_only)
    tail = sum(math.comb(n, index) for index in range(k + 1)) / (2**n)
    return min(1.0, 2 * tail)


def _stage_metrics(root: Path, repair: str, baseline: str) -> dict[str, Any]:
    rows = [json.loads(line) for line in (root / "raw_evaluations.jsonl").read_text(encoding="utf-8").splitlines() if line]
    seed = min(int(row["seed"]) for row in rows)
    attacked = [row for row in rows if int(row["seed"]) == seed and row["condition"] == "attacked"]
    clean = [row for row in rows if int(row["seed"]) == seed and row["condition"] == "clean"]
    by_key = {(row["case_id"], row["arm"], row["condition"]): row for row in attacked + clean}
    cases = sorted({row["case_id"] for row in attacked})
    baseline_attack = [bool(by_key[(case, baseline, "attacked")]["correct"]) for case in cases]
    repair_attack = [bool(by_key[(case, repair, "attacked")]["correct"]) for case in cases]
    repair_clean = [bool(by_key[(case, repair, "clean")]["correct"]) for case in cases]
    baseline_only = sum(base and not fixed for base, fixed in zip(baseline_attack, repair_attack, strict=True))
    repair_only = sum(fixed and not base for base, fixed in zip(baseline_attack, repair_attack, strict=True))
    return {
        "unique_cases": len(cases), "representative_seed": seed,
        "baseline_attacked_correct": sum(baseline_attack),
        "repair_attacked_correct": sum(repair_attack),
        "repair_clean_correct": sum(repair_clean),
        "baseline_attacked_accuracy": sum(baseline_attack) / len(cases),
        "repair_attacked_recovery_accuracy": sum(repair_attack) / len(cases),
        "repair_clean_accuracy": sum(repair_clean) / len(cases),
        "repair_attacked_wilson_95": wilson(sum(repair_attack), len(cases)),
        "repair_clean_wilson_95": wilson(sum(repair_clean), len(cases)),
        "mcnemar_exact_two_sided_p": exact_mcnemar(baseline_only, repair_only),
        "mcnemar_discordant": {"baseline_only": baseline_only, "repair_only": repair_only},
        "seed_repetitions_not_independent": True,
    }


def generate(output: Path) -> tuple[Path, Path]:
    """Verify every core bundle and generate JSON plus human-readable Markdown."""
    if output.exists():
        raise FileExistsError(f"causal-core report output exists: {output}")
    core02_root = ROOT / "results/phase1/search_comparison"
    verifications: dict[str, Any] = {"matched_search": verify_core02(core02_root)}
    metrics: dict[str, Any] = {}
    evidence_hashes: dict[str, dict[str, str]] = {
        "matched_search": {name: _sha256(core02_root / name) for name in ("summary.json", "search_results.json", "manifest.json")}
    }
    for name, (root, repair, baseline, verifier) in STAGES.items():
        verifications[name] = verifier(root)
        metrics[name] = _stage_metrics(root, repair, baseline)
        evidence_hashes[name] = {artifact: _sha256(root / artifact) for artifact in
                                 ("summary.json", "arm_results.json", "manifest.json", "raw_evaluations.jsonl")}
    search_results = json.loads((core02_root / "search_results.json").read_text(encoding="utf-8"))
    search_summary = {}
    for method in ("greedy", "matched_random", "beam", "flat_ppo", "receiver_only"):
        rows = [value for key, value in search_results.items() if key.startswith(method + ":")]
        search_summary[method] = {
            "retained_masks": [row["retained"] for row in rows],
            "faithfulness": [row["evaluation"]["faithfulness"] for row in rows],
            "forward_passes": [row["evaluation"]["forward_passes"] for row in rows],
        }
    status = execution_status()
    incomplete = [row["id"] for row in status["stages"] if row["readiness"] != "COMPLETE"]
    payload = {
        "schema_version": "aether.causal-core-report.v1", "overall": "PASS",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "verification": verifications, "metrics": metrics,
        "matched_search": search_summary, "evidence_sha256": evidence_hashes,
        "supported_claim": "The frozen paired-clean-donor receiver L20H5 repair recovered attacked decisions on development-audit, locked-validation, and once-only-test cohorts of the frozen balanced synthetic task.",
        "non_claims": ["oracle-free deployable defense", "clinical or population validity",
                       "global circuit minimality", "complete distributed internal circuit",
                       "second-model generalization", "official external benchmark performance"],
        "remaining_phase1_gates": incomplete,
        "phase1_overall_evidence": status["overall_evidence"],
    }
    output.mkdir(parents=True)
    json_path = output / "causal_core_report.json"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = ["# AETHER verified causal-core report", "", "## Outcome", "",
             payload["supported_claim"], "", "## Cohort results", "",
             "| Cohort | Unique cases | Baseline attacked | L20H5 attacked recovery | Clean accuracy | Wilson 95% recovery | Exact McNemar p |",
             "|---|---:|---:|---:|---:|---:|---:|"]
    for name, row in metrics.items():
        interval = row["repair_attacked_wilson_95"]
        lines.append(f"| {name.replace('_', ' ')} | {row['unique_cases']} | {row['baseline_attacked_accuracy']:.3f} | {row['repair_attacked_recovery_accuracy']:.3f} | {row['repair_clean_accuracy']:.3f} | [{interval[0]:.3f}, {interval[1]:.3f}] | {row['mcnemar_exact_two_sided_p']:.6f} |")
    lines.extend(["", "Seeds 11, 22 and 33 are deterministic repetitions and are not treated as independent cases.",
                  "", "## Claim limits", ""] + [f"- Does not establish {item}." for item in payload["non_claims"]] +
                 ["", "## Remaining Phase-1 gates", ""] + [f"- `{item}`" for item in incomplete])
    md_path = output / "CAUSAL_CORE_REPORT.md"; md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    labels = list(metrics)
    svg = ["<svg xmlns='http://www.w3.org/2000/svg' width='900' height='420' viewBox='0 0 900 420'>",
           "<rect width='900' height='420' fill='white'/>",
           "<text x='450' y='32' text-anchor='middle' font-family='sans-serif' font-size='20'>AETHER causal repair across frozen cohorts</text>",
           "<line x1='90' y1='350' x2='850' y2='350' stroke='#222'/>",
           "<line x1='90' y1='70' x2='90' y2='350' stroke='#222'/>",
           "<text x='35' y='215' transform='rotate(-90 35 215)' text-anchor='middle' font-family='sans-serif'>Attacked decision recovery</text>"]
    for index, name in enumerate(labels):
        row = metrics[name]; centre = 210 + index * 230
        baseline_height = 260 * row["baseline_attacked_accuracy"]
        repair_height = 260 * row["repair_attacked_recovery_accuracy"]
        svg.extend([
            f"<rect x='{centre-65}' y='{350-baseline_height}' width='55' height='{baseline_height}' fill='#9aa0a6'/>",
            f"<rect x='{centre+10}' y='{350-repair_height}' width='55' height='{repair_height}' fill='#1565c0'/>",
            f"<text x='{centre}' y='378' text-anchor='middle' font-family='sans-serif' font-size='12'>{name.replace('_', ' ')}</text>",
            f"<text x='{centre-38}' y='{340-baseline_height}' text-anchor='middle' font-family='sans-serif' font-size='12'>{row['baseline_attacked_accuracy']:.1f}</text>",
            f"<text x='{centre+38}' y='{340-repair_height}' text-anchor='middle' font-family='sans-serif' font-size='12'>{row['repair_attacked_recovery_accuracy']:.1f}</text>",
        ])
    svg.extend(["<rect x='600' y='55' width='16' height='16' fill='#9aa0a6'/><text x='622' y='68' font-family='sans-serif' font-size='12'>No defense</text>",
                "<rect x='700' y='55' width='16' height='16' fill='#1565c0'/><text x='722' y='68' font-family='sans-serif' font-size='12'>L20H5 repair</text>", "</svg>"])
    (output / "causal_core_recovery.svg").write_text("".join(svg), encoding="utf-8")
    return json_path, md_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "results/phase1/causal_core_report")
    paths = generate(parser.parse_args().output.resolve()); print("\n".join(str(path) for path in paths))


if __name__ == "__main__":
    main()
