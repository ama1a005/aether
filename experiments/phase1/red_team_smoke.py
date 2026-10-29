"""Manifest-backed four-family red-team software acceptance, no model downloads."""
import argparse
from pathlib import Path
from uuid import uuid4

import yaml

from attacks.backends import RuleBasedBackend
from attacks.corpus.attack_store import AttackStore
from attacks.corpus.builder import CorpusBuilder
from attacks.orchestration import CampaignConfig, run_campaign
from contracts.schemas import PatientCase


def run(config_path: Path, output_root: Path) -> dict[str, object]:
    """Execute actual rule agents on explicitly synthetic critical cases."""
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if config["backend"] != "rule_based" or config["split"] != "synthetic":
        raise ValueError("Core smoke runner requires explicit rule-based synthetic mode")
    campaign = CampaignConfig(config["experiment_id"], config["seed"],
                              config["max_target_calls"], config["split"])
    output_root.mkdir(parents=True, exist_ok=True)
    run_id = f"{campaign.experiment_id}_{uuid4().hex}"
    store = AttackStore(str(output_root / f"{run_id}_corpus"))
    attacks = CorpusBuilder(campaign.seed).build_phase1_corpus(store, config["n_per_family"])
    cases = [PatientCase("synthetic_critical", {"heart_rate": 130}, "ESCALATE",
                         source_dataset="synthetic", fixture_only=True)]
    backend = RuleBasedBackend()
    return run_campaign(backend, cases, attacks, campaign, output_root / run_id)


def main() -> None:
    """Run the portable red-team acceptance command."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/experiments/red_team_synthetic.yaml"))
    parser.add_argument("--output-root", type=Path, default=Path(".local/red_team"))
    args = parser.parse_args()
    print(run(args.config, args.output_root))


if __name__ == "__main__":
    main()
