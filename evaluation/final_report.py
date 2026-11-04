"""Generate Phase 1 tables only from verified manifests and raw outcomes."""
from __future__ import annotations

import argparse
import csv
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from typing import Sequence

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import yaml

from evaluation.phase1_statistics import OutcomeRecord, paired_method_comparison, summarize_outcomes


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_run(run_dir: Path, *, require_clean_git: bool) -> tuple[dict, list[OutcomeRecord]]:
    """Verify manifest identity/hashes and load standardized outcome rows."""
    manifest_path = run_dir / "manifest.json"
    outcomes_path = run_dir / "outcomes.json"
    if not manifest_path.is_file() or not outcomes_path.is_file():
        raise FileNotFoundError(f"Run lacks manifest.json or outcomes.json: {run_dir}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    required = {"experiment_id", "run_id", "git_commit", "dataset_manifest_hashes",
                "model_id", "model_revision", "tokenizer_revision", "random_seeds",
                "python_env_hash", "config_hash", "artifact_paths"}
    missing = required - manifest.keys()
    if missing:
        raise ValueError(f"Manifest is incomplete: {sorted(missing)}")
    if require_clean_git and manifest.get("uncommitted_diff") is not False:
        raise ValueError("Final report rejects runs from a dirty worktree")
    if not manifest["dataset_manifest_hashes"] or not manifest["random_seeds"]:
        raise ValueError("Dataset hashes and seeds are required")
    artifacts = manifest["artifact_paths"]
    matched_outcomes = False
    for raw_path, expected in artifacts.items():
        path = Path(raw_path)
        if not path.is_absolute():
            path = run_dir / path
        if not path.is_file() or _sha256(path) != expected:
            raise ValueError(f"Artifact hash mismatch or missing file: {path}")
        matched_outcomes |= path.resolve() == outcomes_path.resolve()
    if not matched_outcomes:
        raise ValueError("Manifest does not hash outcomes.json")
    payload = json.loads(outcomes_path.read_text(encoding="utf-8"))
    if payload.get("run_id") != manifest["run_id"] or not isinstance(payload.get("records"), list):
        raise ValueError("Outcome payload identity or records are invalid")
    return manifest, [OutcomeRecord(**row) for row in payload["records"]]


def generate_report(config_path: Path, run_dirs: Sequence[Path], output_dir: Path) -> Path:
    """Create JSON/CSV/PNG summaries after every declared gate passes."""
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if config.get("schema_version") != 1 or config.get("split") not in {"development", "validation", "test"}:
        raise ValueError("Final report configuration is invalid")
    manifests = []
    records = []
    for run_dir in run_dirs:
        manifest, rows = verify_run(run_dir, require_clean_git=config["require_clean_git"])
        manifests.append(manifest)
        records.extend(rows)
    observed = {manifest["experiment_id"] for manifest in manifests}
    required = set(config["required_experiment_ids"])
    if observed != required:
        raise ValueError(f"Experiment set mismatch; required={sorted(required)}, observed={sorted(observed)}")
    if any(manifest.get("dataset_split") != config["split"] for manifest in manifests):
        raise ValueError("Run split does not match report split")
    summary = summarize_outcomes(records, bootstrap_seed=config["bootstrap_seed"],
                                 bootstrap_samples=config["bootstrap_samples"])
    comparisons = [paired_method_comparison(records, pair[0], pair[1])
                   for pair in config["paired_method_comparisons"]]
    output_dir.mkdir(parents=True, exist_ok=False)
    report = {"schema_version": 1, "split": config["split"],
              "run_ids": [item["run_id"] for item in manifests],
              "statistics": summary, "paired_comparisons": comparisons,
              "source_records": [asdict(row) for row in records]}
    destination = output_dir / "phase1_report.json"
    destination.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False),
                           encoding="utf-8")
    with (output_dir / "method_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = ["method", *next(iter(summary.values())).keys()]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows({"method": method, **values} for method, values in summary.items())
    methods = list(summary)
    values = [summary[method]["asr"] or 0.0 for method in methods]
    figure, axis = plt.subplots(figsize=(max(5, len(methods) * 1.2), 4))
    axis.bar(methods, values)
    axis.set_ylim(0, 1)
    axis.set_ylabel("Attack success rate")
    axis.set_title(f"Phase 1 {config['split']} outcomes")
    figure.tight_layout()
    figure.savefig(output_dir / "asr_by_method.png", dpi=150)
    plt.close(figure)
    return destination


def main() -> None:
    """CLI for manifest-gated report generation."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, action="append", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(generate_report(args.config, args.run_dir, args.output_dir))


if __name__ == "__main__":
    main()
