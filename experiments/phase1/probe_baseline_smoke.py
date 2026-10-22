"""Run the model-free linear-probe software acceptance.

The generated arrays are synthetic development data. Outputs verify mechanics
only and must not be reported as model, benchmark, or causal evidence.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
from time import perf_counter
from uuid import uuid4

import numpy as np
import yaml

from evaluation.linear_probe import ProbeData, evaluate_probe, fit_linear_probe, permutation_controls
from experiments.manifest import create_run_manifest, write_run_manifest

ROOT = Path(__file__).resolve().parents[2]


def _generate(seed: int, samples: int, noise_features: int, prefix: str) -> ProbeData:
    """Generate a declared signal plus independent Gaussian nuisance features."""
    rng = np.random.default_rng(seed)
    labels = np.tile([0, 1], samples // 2 + 1)[:samples]
    rng.shuffle(labels)
    signal = (2 * labels - 1).astype(np.float64) + rng.normal(0.0, 0.2, samples)
    noise = rng.normal(size=(samples, noise_features))
    features = np.column_stack((signal, noise))
    return ProbeData(features, labels, tuple(f"{prefix}-{index}" for index in range(samples)),
                     ("declared_signal", *(f"noise_{index}" for index in range(noise_features))),
                     "development")


def run(config_path: Path, output_root: Path | None = None) -> Path:
    """Execute acceptance and write raw metrics plus a reproducibility manifest."""
    config_path = config_path.resolve()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if config["evidence_class"] != "synthetic_acceptance_only" or config["split"] != "synthetic_development":
        raise ValueError("This entry point accepts synthetic development configurations only")
    started = perf_counter()
    fit = _generate(config["seed"], config["fit_samples"], config["noise_features"], "fit")
    evaluation = _generate(config["seed"] + 1, config["evaluation_samples"],
                           config["noise_features"], "evaluation")
    probe = fit_linear_probe(fit, l2=config["l2"])
    metrics = evaluate_probe(probe, fit, evaluation)
    controls = permutation_controls(fit, evaluation, seeds=config["permutation_seeds"], l2=config["l2"])
    checks = {
        "probe_outperforms_all_permutations_auroc": all(metrics.auroc > item.auroc for item in controls),
        "probe_outperforms_all_permutations_pr_auc": all(metrics.pr_auc > item.pr_auc for item in controls),
        "fit_and_evaluation_ids_disjoint": not (set(fit.sample_ids) & set(evaluation.sample_ids)),
        "feature_provenance_matches": fit.feature_ids == evaluation.feature_ids,
    }
    run_id = f"{config['experiment_id']}_{uuid4().hex}"
    destination = (output_root or ROOT / config["output_root"]) / run_id
    destination.mkdir(parents=True, exist_ok=False)
    output = destination / "results.json"
    payload = {
        "run_id": run_id,
        "utc_timestamp": datetime.now(timezone.utc).isoformat(),
        "evidence_class": config["evidence_class"],
        "checks": checks,
        "metrics": asdict(metrics),
        "permutation_controls": [asdict(item) for item in controls],
        "fit_sample_ids": list(fit.sample_ids),
        "evaluation_sample_ids": list(evaluation.sample_ids),
        "feature_ids": list(fit.feature_ids),
        "validation_executions": 0,
        "test_executions": 0,
        "claim_limit": "Synthetic software acceptance only; predictive probes are correlational, not causal.",
    }
    output.write_text(json.dumps(payload, indent=2, allow_nan=False), encoding="utf-8")
    manifest = create_run_manifest(
        experiment_id=config["experiment_id"], run_id=run_id,
        model_id="synthetic_linear_signal", model_revision="v1", tokenizer_revision="not_applicable",
        dataset_id="synthetic_probe_acceptance", dataset_version="v1", dataset_split=config["split"],
        subset_ids=["generated_fit", "generated_evaluation"],
        seeds=[config["seed"], config["seed"] + 1, *config["permutation_seeds"]],
        config_file=config_path, raw_output_path=output,
        dataset_files=[Path(__file__).resolve()],
        search_config={"baseline": "l2_logistic_probe", "l2": config["l2"],
                       "fit_samples": config["fit_samples"],
                       "evaluation_samples": config["evaluation_samples"],
                       "permutation_seeds": config["permutation_seeds"]},
        intervention_config={"operator": "none", "evidence_type": "correlational_probe"},
        artifact_paths=[output, ROOT / "evaluation/linear_probe.py"],
        timing_seconds={"execution": perf_counter() - started}, repository=ROOT)
    write_run_manifest(manifest, destination / "manifest.json")
    if not all(checks.values()):
        raise RuntimeError(f"Probe acceptance failed; evidence saved in {destination}")
    return destination


def main() -> None:
    """Run configured acceptance and print its artifact directory."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path,
                        default=ROOT / "configs/experiments/probe_baseline_synthetic.yaml")
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args()
    print(f"PROBE BASELINE ACCEPTANCE PASSED: {run(args.config, args.output_root)}")


if __name__ == "__main__":
    main()
