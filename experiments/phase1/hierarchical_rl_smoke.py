"""Run manifest-backed multi-seed acceptance for hierarchical graph PPO."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
from time import perf_counter
from uuid import uuid4

import yaml

from discovery.budgeted import Candidate, Evaluation, SearchConfig
from discovery.rl.hierarchical import CausalEdge, GraphSearchState, hierarchical_ppo_search
from discovery.rl.ppo import PPOConfig, RewardWeights
from experiments.manifest import create_run_manifest, write_run_manifest

ROOT = Path(__file__).resolve().parents[2]
CANDIDATES = tuple(Candidate(identifier, region) for identifier, region in (
    ("S", "sender"), ("S_noise", "sender"), ("M", "message"),
    ("M_noise", "message"), ("R", "receiver"), ("R_noise", "receiver")))
EDGES = (CausalEdge("S_M", "S", "M", bridge=True),
         CausalEdge("M_R", "M", "R", bridge=True),
         CausalEdge("SN_MN", "S_noise", "M_noise", bridge=True),
         CausalEdge("MN_RN", "M_noise", "R_noise", bridge=True))


def evaluate_state(state: GraphSearchState) -> Evaluation:
    """Measure a declared path in a branching deterministic graph."""
    path = ({"S", "M", "R"} <= set(state.active_nodes)
            and {"S_M", "M_R"} <= set(state.active_edges))
    return Evaluation(float(path), 0.0, 2, asdict(state))


def run(config_path: Path, output_root: Path | None = None) -> Path:
    """Execute all declared seeds and save raw graph states plus a manifest."""
    config_path = config_path.resolve()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if config["split"] != "synthetic" or config["evidence_class"] != "synthetic_acceptance_only":
        raise ValueError("Hierarchical RL smoke accepts synthetic evidence only")
    started = perf_counter()
    outcomes = {}
    for seed in config["seeds"]:
        search = SearchConfig(config["max_queries"], config["faithfulness_threshold"],
                              config["max_benign_damage"], split=config["split"])
        ppo = PPOConfig(seed=seed, training_steps=config["training_steps"],
                        rollout_steps=config["rollout_steps"], update_epochs=config["update_epochs"],
                        hidden_size=config["hidden_size"], learning_rate=config["learning_rate"])
        outcome = hierarchical_ppo_search(CANDIDATES, EDGES, evaluate_state, search, ppo,
                                          RewardWeights(**config["reward"]),
                                          node_operators=config["node_operators"])
        outcomes[str(seed)] = asdict(outcome)
    expected = ("M", "R", "S")
    checks = {
        "all_seeds_feasible": all(item["result"]["feasible"] for item in outcomes.values()),
        "all_seeds_recover_path": all(tuple(item["result"]["retained"]) == expected
                                       for item in outcomes.values()),
        "all_seeds_respect_budget": all(item["result"]["queries"] <= config["max_queries"]
                                         for item in outcomes.values()),
        "typed_operations_exercised": all(
            {row["action"]["operation"] for row in item["training_trace"]}
            <= {"node_intervention", "edge_cut", "stop"} for item in outcomes.values()),
        "graph_records_retained": all(item["graph_records"] for item in outcomes.values()),
        "local_repair_verified": all(item["repair_complete"] for item in outcomes.values()),
    }
    run_id = f"{config['experiment_id']}_{uuid4().hex}"
    destination = (output_root or ROOT / config["output_root"]) / run_id
    destination.mkdir(parents=True, exist_ok=False)
    output = destination / "results.json"
    payload = {"run_id": run_id, "utc_timestamp": datetime.now(timezone.utc).isoformat(),
               "evidence_class": config["evidence_class"], "checks": checks,
               "outcomes": outcomes, "validation_executions": 0, "test_executions": 0,
               "claim_limit": "Synthetic software acceptance; PPO/RL is not a novelty claim."}
    output.write_text(json.dumps(payload, indent=2, allow_nan=False), encoding="utf-8")
    manifest = create_run_manifest(
        experiment_id=config["experiment_id"], run_id=run_id,
        model_id="synthetic_branching_dcmg", model_revision="v1",
        tokenizer_revision="not_applicable", dataset_id="synthetic_hierarchical_rl",
        dataset_version="v1", dataset_split="synthetic", subset_ids=["branching_path"],
        seeds=config["seeds"], config_file=config_path, raw_output_path=output,
        dataset_files=[Path(__file__).resolve()],
        search_config={key: config[key] for key in ("max_queries", "faithfulness_threshold",
                                                     "max_benign_damage", "training_steps",
                                                     "rollout_steps", "update_epochs")},
        intervention_config={"node_operators": config["node_operators"],
                             "edge_operator": "cut", "action_factorization":
                             ["operation", "region", "target", "operator"]},
        artifact_paths=[output, ROOT / "discovery/rl/hierarchical.py"],
        timing_seconds={"execution": perf_counter() - started}, repository=ROOT)
    write_run_manifest(manifest, destination / "manifest.json")
    if not all(checks.values()):
        raise RuntimeError(f"Hierarchical RL acceptance failed; evidence retained at {destination}")
    return destination


def main() -> None:
    """CLI for synthetic hierarchical graph-RL acceptance."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path,
                        default=ROOT / "configs/experiments/hierarchical_rl_synthetic.yaml")
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args()
    print(f"HIERARCHICAL RL ACCEPTANCE PASSED: {run(args.config, args.output_root)}")


if __name__ == "__main__":
    main()
