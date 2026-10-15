"""Create post-run V2 evidence and pivot summaries from executed artifacts."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from experiments.manifest import sha256_file

ROOT = Path("results/phase1/balanced_v2")


def main() -> None:
    """Summarize executed development evidence without inventing internal effects."""
    summary_path = ROOT / "full_v2_1/summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    evidence = []
    for direction, values in summary["message_controls_by_direction"].items():
        evidence.append({
            "edge_id": f"message.decision_code->receiver.outcome.{direction}",
            "source_type": "message_field", "target_type": "outcome",
            "evidence_type": "message_intervention", "operator": "whole_message_rescue_and_induction",
            "split": "development", "attack_direction": direction,
            "n_eligible": values["N_eligible"],
            "rescue_effects": values["clean_message_rescue"],
            "induction_effects": values["attacked_message_induction"],
            "status": "supported",
        })
    for role, target in (("sender_internal", "message.decision_code"), ("receiver_internal", "receiver.outcome")):
        evidence.append({
            "edge_id": f"{role}->{target}", "source_type": role, "target_type": target,
            "evidence_type": "not_executed_behavioral_gate_failed", "operator": None,
            "split": "development", "attack_direction": "both",
            "n_eligible": 0, "effect_values": [], "status": "insufficient",
        })
    evidence_path = ROOT / "revised_dcmg_evidence.json"
    evidence_path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    pivot = {
        "result_state": "DEV", "validation_test_accessed": False,
        "behavioral_gate": "failed_asymmetric_clean_competence_and_attack_success",
        "candidate_classifications": {"sender": "INSUFFICIENT", "receiver": "INSUFFICIENT"},
        "maximum_pathway_bvp_level": 1,
        "sender_to_mediator_level_2": "insufficient_not_executed",
        "receiver_to_outcome_level_3": "insufficient_not_executed",
        "internal_scan_executed": False, "head_refinement_executed": False,
        "recommendation": "PIVOT_PHASE_1", "utc_timestamp": datetime.now(timezone.utc).isoformat(),
    }
    pivot_path = ROOT / "pivot_summary.json"
    pivot_path.write_text(json.dumps(pivot, indent=2), encoding="utf-8")
    manifest = {
        "manifest_version": "1.0.0", "run_id": "P0_cross_20261015_balanced_v2_pivot_0",
        "utc_timestamp": pivot["utc_timestamp"], "git_commit": "303e0d8", "uncommitted_diff": True,
        "source_summary": str(summary_path), "source_summary_hash": sha256_file(summary_path),
        "freeze_manifest": "data/causal_v2/freeze_manifest_v2_1.json",
        "freeze_manifest_hash": sha256_file(Path("data/causal_v2/freeze_manifest_v2_1.json")),
        "split": "development", "validation_test_accessed": False,
        "artifacts": {str(evidence_path): sha256_file(evidence_path), str(pivot_path): sha256_file(pivot_path)},
    }
    (ROOT / "pivot_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(pivot, indent=2))


if __name__ == "__main__":
    main()
