"""Demo-owned full red-team campaign over real MCP SDK stdio transport."""
import argparse
from pathlib import Path
from uuid import uuid4

import yaml

from attacks.corpus.attack_store import AttackStore
from attacks.corpus.builder import CorpusBuilder
from attacks.orchestration import CampaignConfig, run_campaign
from contracts.schemas import PatientCase
from demo.backend.red_team_backend import DemoMCPRuleBackend
from demo.backend.repository import load_cases


def run(config_path: Path, output_root: Path) -> dict[str, object]:
    """Execute all four families against one synthetic case through real MCP."""
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if config["backend"] != "demo_mcp_stdio" or config["split"] != "synthetic":
        raise ValueError("Demo MCP runner requires explicit demo_mcp_stdio synthetic mode")
    campaign = CampaignConfig(config["experiment_id"], config["seed"],
                              config["max_target_calls"], config["split"])
    output_root.mkdir(parents=True, exist_ok=True)
    run_id = f"{campaign.experiment_id}_{uuid4().hex}"
    store = AttackStore(str(output_root / f"{run_id}_corpus"))
    attacks = CorpusBuilder(campaign.seed).build_phase1_corpus(store, config["n_per_family"])
    source = next(case for case in load_cases() if case.expected_action == "ESCALATE")
    cases = [PatientCase(source.case_id, {}, source.expected_action,
                         source_dataset=source.dataset_origin, fixture_only=True)]
    return run_campaign(DemoMCPRuleBackend(), cases, attacks, campaign, output_root / run_id)


def main() -> None:
    """Run the complete synthetic MCP transport acceptance."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path,
                        default=Path("configs/experiments/red_team_mcp_synthetic.yaml"))
    parser.add_argument("--output-root", type=Path, default=Path(".local/red_team_mcp"))
    args = parser.parse_args()
    print(run(args.config, args.output_root))


if __name__ == "__main__":
    main()
