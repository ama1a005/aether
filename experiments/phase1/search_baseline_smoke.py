"""Execute synthetic search acceptance with raw queries and an automatic manifest.

This tests search mechanics on a declared multiplicative toy system. It does not
access model activations, external benchmarks, or any frozen data split.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
from time import perf_counter
from uuid import uuid4

import yaml

from causal.metrics.faithfulness import compute_faithfulness
from discovery.budgeted import Candidate, Evaluation, SearchConfig, random_control, receiver_candidates, search
from experiments.manifest import create_run_manifest, write_run_manifest

ROOT = Path(__file__).resolve().parents[2]
CANDIDATES = tuple(Candidate(name, region) for name, region in (
    ("S", "sender"), ("S_noise", "sender"), ("M", "message"),
    ("M_noise", "message"), ("R", "receiver"), ("R_noise", "receiver")))


def evaluate_mask(mask: tuple[str, ...]) -> Evaluation:
    """Execute clean/attack/reconstructed/benign toy forwards for one mask.

    Each ablated node has value zero. The unsafe score is S*M*R; all noise
    nodes are irrelevant by construction. Receiver-only actions use this same
    evaluator with sender/message nodes absent (zero), an explicit limitation.
    """
    def forward(active: set[str], benign: bool = False) -> float:
        return float(("S" in active) * ("M" in active) * ("R" in active) * (not benign))

    clean = forward(set())
    attacked = forward({candidate.id for candidate in CANDIDATES})
    reconstructed = forward(set(mask))
    benign = forward(set(mask), benign=True)
    return Evaluation(float(compute_faithfulness(attacked - clean, reconstructed - clean)),
                      abs(benign - clean), 4,
                      {"clean": clean, "attacked": attacked, "reconstructed": reconstructed,
                       "benign_intervened": benign, "retained": list(mask)})


def run(config_path: Path, output_root: Path | None = None) -> Path:
    """Run all search baselines and preserve artifacts in a fresh run directory."""
    config_path = config_path.resolve()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if config["evidence_class"] != "synthetic_acceptance_only" or config["split"] != "synthetic":
        raise ValueError("This entry point accepts synthetic acceptance configurations only")
    settings = SearchConfig(max_queries=config["max_queries"], beam_width=config["beam_width"],
                            faithfulness_threshold=config["faithfulness_threshold"],
                            max_benign_damage=config["max_benign_damage"], split=config["split"])
    started = perf_counter()
    results = {method: search(CANDIDATES, evaluate_mask, settings, method=method)
               for method in ("greedy", "beam")}
    results["receiver_only"] = search(receiver_candidates(CANDIDATES), evaluate_mask, settings)
    results["matched_random"] = random_control(CANDIDATES, evaluate_mask, settings,
        results["greedy"].retained, samples=config["random_samples"], seed=config["seed"])
    checks = {
        "greedy_recovers_declared_path": set(results["greedy"].retained) == {"S", "M", "R"},
        "beam_recovers_declared_path": set(results["beam"].retained) == {"S", "M", "R"},
        "all_budgets_respected": all(result.queries <= settings.max_queries for result in results.values()),
        "receiver_only_honestly_infeasible": not results["receiver_only"].feasible,
        "local_minimality_verified": all(results[method].one_step_locally_minimal for method in ("greedy", "beam")),
    }
    run_id = f"{config['experiment_id']}_{uuid4().hex}"
    destination = (output_root or ROOT / config["output_root"]) / run_id
    destination.mkdir(parents=True, exist_ok=False)
    output = destination / "results.json"
    payload = {"run_id": run_id, "utc_timestamp": datetime.now(timezone.utc).isoformat(),
               "evidence_class": config["evidence_class"], "checks": checks,
               "results": {name: asdict(result) for name, result in results.items()},
               "validation_executions": 0, "test_executions": 0,
               "comparison_limit": "Synthetic mechanics only; receiver-only cannot reconstruct a product whose sender/message inputs are zero. No empirical DCMG superiority claim."}
    output.write_text(json.dumps(payload, indent=2, allow_nan=False), encoding="utf-8")
    manifest = create_run_manifest(experiment_id=config["experiment_id"], run_id=run_id,
        model_id="synthetic_multiplicative_system", model_revision="v1", tokenizer_revision="not_applicable",
        dataset_id="synthetic_search_acceptance", dataset_version="v1", dataset_split="synthetic",
        subset_ids=["multiplicative_path"], seeds=[config["seed"]], config_file=config_path,
        raw_output_path=output, dataset_files=[Path(__file__).resolve()],
        search_config={**asdict(settings), "query_unit": "one mask over a fixed evaluator",
                       "random_samples": config["random_samples"]},
        intervention_config={"operator": "zero_excluded_nodes", "held_fixed": "toy_equations"},
        artifact_paths=[output, ROOT / "discovery/budgeted.py"],
        timing_seconds={"execution": perf_counter() - started}, repository=ROOT)
    write_run_manifest(manifest, destination / "manifest.json")
    if not all(checks.values()):
        raise RuntimeError(f"Search acceptance failed; evidence saved in {destination}")
    return destination


def main() -> None:
    """Run the configured acceptance and print its artifact directory."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/experiments/search_baselines_synthetic.yaml")
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args()
    print(f"SEARCH BASELINE ACCEPTANCE PASSED: {run(args.config, args.output_root)}")


if __name__ == "__main__":
    main()
