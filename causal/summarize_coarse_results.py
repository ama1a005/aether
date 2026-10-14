"""Derive baseline/control comparisons from immutable coarse-scan rows."""

from __future__ import annotations

import json
from pathlib import Path

from experiments.manifest import sha256_file

ROOT = Path("results/phase1/causal_discovery")


def main() -> None:
    """Write comparison metrics without rerunning model interventions."""
    summary = json.loads((ROOT / "summary.json").read_text(encoding="utf-8"))
    sender = json.loads((ROOT / "sender_scan.json").read_text(encoding="utf-8"))
    receiver = json.loads((ROOT / "receiver_scan.json").read_text(encoding="utf-8"))
    sender_by_id = {row["candidate_id"]: row for row in sender}
    receiver_by_id = {row["candidate_id"]: row for row in receiver}
    sender_controls = [{"candidate_id": candidate, "decision_recovery_mean": sender_by_id[candidate]["decision_recovery"]["mean"], "downstream_recovery_median": sender_by_id[candidate]["downstream_recovery"]["median"]} for candidate in summary["matched_controls"]["sender"]]
    receiver_controls = [{"candidate_id": candidate, "recovery_median": receiver_by_id[candidate]["recovery"]["median"], "raw_effect_mean": receiver_by_id[candidate]["raw_effect"]["mean"]} for candidate in summary["matched_controls"]["receiver"]]
    best_sender = sender_by_id[summary["top_k"]["sender"][0]]
    best_receiver = receiver_by_id[summary["top_k"]["receiver"][0]]
    result = {"result_state": "DEV", "evaluation_origin": "aether_positive_control", "message_only_recovery": summary["baselines"]["message_only"]["clean_message_rescue_mean_recovery"], "trace_level_replay_recovery": summary["baselines"]["trace_level_clean_message_replay_recovery"], "best_sender": {"candidate_id": best_sender["candidate_id"], "decision_recovery_mean": best_sender["decision_recovery"]["mean"], "downstream_recovery_median": best_sender["downstream_recovery"]["median"], "clean_utility": best_sender["clean_utility"]}, "best_receiver": {"candidate_id": best_receiver["candidate_id"], "recovery_median": best_receiver["recovery"]["median"], "raw_effect_mean": best_receiver["raw_effect"]["mean"], "clean_utility": best_receiver["clean_utility"]}, "matched_controls": {"sender": sender_controls, "receiver": receiver_controls}, "incremental_value_status": "not_established_on_held_out_data", "interpretation": "Internal interventions localize development sites, but message-only and trace replay both recover 1.0; additional held-out value is unproven."}
    path = ROOT / "comparison.json"
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    manifest_path = ROOT / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifacts"][str(path)] = sha256_file(path)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
