"""Run synthetic PPO/search comparison and reward-ablation acceptance."""

from __future__ import annotations

import argparse
from dataclasses import asdict, replace
from datetime import datetime, timezone
import json
from pathlib import Path
from time import perf_counter
from uuid import uuid4

import yaml

from discovery.budgeted import Candidate, Evaluation, SearchConfig, random_control, search
from discovery.rl.ppo import PPOConfig, RewardWeights, ppo_search_with_trace
from discovery.rl.policy import evaluate_policy, load_policy, save_policy
from experiments.manifest import create_run_manifest, write_run_manifest

ROOT = Path(__file__).resolve().parents[2]
CANDIDATES = tuple(Candidate(identifier, region) for identifier, region in (
    ("S", "sender"), ("S_noise", "sender"), ("M", "message"),
    ("M_noise", "message"), ("R", "receiver"), ("R_noise", "receiver")))


def evaluate_mask(mask: tuple[str, ...]) -> Evaluation:
    """Evaluate one mask on a declared three-node multiplicative path."""
    required = {"S", "M", "R"}
    retained = set(mask)
    return Evaluation(float(required <= retained), 0.0, 4,
                      {"retained": list(mask), "required": sorted(required),
                       "path_active": required <= retained})


def run(config_path: Path, output_root: Path | None = None) -> Path:
    """Execute matched search baselines, PPO, ablations, and a run manifest."""
    config_path = config_path.resolve()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if config["evidence_class"] != "synthetic_acceptance_only" or config["split"] != "synthetic":
        raise ValueError("RL smoke accepts synthetic configurations only")
    search_config = SearchConfig(config["max_queries"], config["faithfulness_threshold"],
                                 config["max_benign_damage"], config["beam_width"], config["split"])
    ppo_config = PPOConfig(seed=config["seed"], training_steps=config["training_steps"],
                           rollout_steps=config["rollout_steps"], update_epochs=config["update_epochs"],
                           hidden_size=config["hidden_size"], learning_rate=config["learning_rate"])
    weights = RewardWeights(**config["reward"])
    started = perf_counter()
    results = {method: search(CANDIDATES, evaluate_mask, search_config, method=method)
               for method in ("greedy", "beam")}
    ppo = ppo_search_with_trace(CANDIDATES, evaluate_mask, search_config, ppo_config, weights)
    results["ppo"] = ppo.result
    results["matched_random"] = random_control(CANDIDATES, evaluate_mask, search_config,
                                                results["greedy"].retained,
                                                samples=config["random_samples"], seed=config["seed"])
    ablation_weights = {
        "no_size": replace(weights, size=0.0),
        "no_cost": replace(weights, cost=0.0),
        "no_stop_bonus": replace(weights, feasible_stop_bonus=0.0),
    }
    ablation_outcomes = {name: ppo_search_with_trace(CANDIDATES, evaluate_mask, search_config,
                                                     ppo_config, ablation_weights[name])
                         for name in config["ablations"]}
    ablations = {name: outcome.result for name, outcome in ablation_outcomes.items()}
    expected = {"S", "M", "R"}
    checks = {
        "ppo_found_declared_path": set(results["ppo"].retained) == expected,
        "ppo_feasible": results["ppo"].feasible,
        "all_methods_respect_query_budget": all(item.queries <= search_config.max_queries
                                                  for item in (*results.values(), *ablations.values())),
        "all_raw_queries_retained": all(all(record.evaluation.raw_outputs for record in item.records)
                                        for item in (*results.values(), *ablations.values())),
        "reward_ablations_executed": set(ablations) == set(config["ablations"]),
    }
    run_id = f"{config['experiment_id']}_{uuid4().hex}"
    destination = (output_root or ROOT / config["output_root"]) / run_id
    destination.mkdir(parents=True, exist_ok=False)
    checkpoint = destination / "ppo_policy.json"
    save_policy(ppo.policy, checkpoint)
    results["ppo_frozen_policy"] = evaluate_policy(
        load_policy(checkpoint), CANDIDATES, evaluate_mask, search_config)
    checks["frozen_policy_respects_query_budget"] = (
        results["ppo_frozen_policy"].queries <= search_config.max_queries)
    checks["frozen_policy_raw_queries_retained"] = all(
        record.evaluation.raw_outputs for record in results["ppo_frozen_policy"].records)
    output = destination / "results.json"
    payload = {"run_id": run_id, "utc_timestamp": datetime.now(timezone.utc).isoformat(),
               "evidence_class": config["evidence_class"], "checks": checks,
               "reward_weights": asdict(weights),
               "results": {name: asdict(value) for name, value in results.items()},
               "ppo_training_trace": [asdict(value) for value in ppo.training_trace],
               "reward_ablations": {name: asdict(value) for name, value in ablations.items()},
               "reward_ablation_training_traces": {
                   name: [asdict(value) for value in outcome.training_trace]
                   for name, outcome in ablation_outcomes.items()},
               "validation_executions": 0, "test_executions": 0,
               "claim_limit": "Synthetic software acceptance only. RL is a prior-art search baseline, not an AETHER novelty claim."}
    output.write_text(json.dumps(payload, indent=2, allow_nan=False), encoding="utf-8")
    manifest = create_run_manifest(
        experiment_id=config["experiment_id"], run_id=run_id,
        model_id="synthetic_multiplicative_system", model_revision="v1",
        tokenizer_revision="not_applicable", dataset_id="synthetic_rl_acceptance",
        dataset_version="v1", dataset_split="synthetic", subset_ids=["three_node_path"],
        seeds=[config["seed"]], config_file=config_path, raw_output_path=output,
        dataset_files=[Path(__file__).resolve()],
        search_config={"shared": asdict(search_config), "ppo": asdict(ppo_config),
                       "reward": asdict(weights), "ablations": config["ablations"]},
        intervention_config={"operator": "zero_excluded_nodes", "query_unit": "unique_mask"},
        artifact_paths=[output, checkpoint, ROOT / "discovery/rl/ppo.py",
                        ROOT / "discovery/rl/policy.py"],
        timing_seconds={"execution": perf_counter() - started}, repository=ROOT)
    write_run_manifest(manifest, destination / "manifest.json")
    if not all(checks.values()):
        raise RuntimeError(f"RL acceptance failed; evidence saved in {destination}")
    return destination


def main() -> None:
    """Run configured synthetic acceptance and print its artifact directory."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path,
                        default=ROOT / "configs/experiments/rl_search_synthetic.yaml")
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args()
    print(f"RL SEARCH ACCEPTANCE PASSED: {run(args.config, args.output_root)}")


if __name__ == "__main__":
    main()
