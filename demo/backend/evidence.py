"""Read-only adapters for committed scientific evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _read(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def evidence_cards() -> list[dict[str, Any]]:
    """Return concise cards computed from actual committed artifacts."""
    core02 = _read("results/phase1/search_comparison/summary.json")
    core03 = _read("results/phase1/remediation/summary.json")
    core04 = _read("results/phase1/locked_validation/summary.json")
    core04_stats = _read("results/phase1/locked_validation/statistics.json")
    core05 = _read("results/phase1/once_only_test/summary.json")
    core05_stats = _read("results/phase1/once_only_test/statistics.json")
    real = _read("results/manifests/P0_mech_20261012_real_instrumentation_0.json")
    ioi = _read("results/calibration/ioi/summary.json")
    paired = _read("results/phase1/paired_real/summary.json")
    specificity = _read("results/phase1/causal_specificity/summary.json")
    v2 = _read("results/phase1/balanced_v2/full_v2_1/summary.json")
    mcptox = _read("results/phase1/mcptox/smoke/summary.json")
    tamas = _read("results/phase1/tamas/smoke/summary.json")
    mq = _read("results/phase1/model_qualification/v2_mq_hw1_retry/manifest.json")
    sae = _read("results/phase1/sae/qwen15b/summary.json")
    second_model = _read("results/phase1/model_qualification/second_model/summary.json")
    agent_c = _read("results/phase1/agent_c/qwen15b/summary.json")
    return [
        {"title":"CORE-02 Matched Search","status":core02["status"],"provenance_type":"VERIFIED REAL-MODEL DEVELOPMENT EVIDENCE","artifact":"results/phase1/search_comparison/summary.json","details":{"method_seed_runs":core02["method_seed_run_count"],"protected_split_executions":0}},
        {"title":"CORE-03 Development Remediation","status":core03["scientific_outcome"],"provenance_type":"VERIFIED REAL-MODEL DEVELOPMENT-AUDIT EVIDENCE","artifact":"results/phase1/remediation/summary.json","details":{"selected_arm":core03["selected_arm"],"evaluation_rows":core03["raw_evaluation_count"],"model_forwards":core03["model_forward_steps"],"oracle_dependent":not core03["deployable_without_oracle"]}},
        {"title":"CORE-04 Locked Validation","status":core04["scientific_outcome"],"provenance_type":"VERIFIED REAL-MODEL LOCKED-VALIDATION EVIDENCE","artifact":"results/phase1/locked_validation/summary.json","details":{"repair_recovery_by_seed":core04_stats["seed_stability"]["frozen_receiver_l20_h5"],"no_defense_by_seed":core04_stats["seed_stability"]["no_defense"],"evaluation_rows":core04["raw_evaluation_count"],"test_executions":core04["test_executions"]}},
        {"title":"CORE-05 Once-Only Test","status":core05["scientific_outcome"],"provenance_type":"VERIFIED REAL-MODEL ONCE-ONLY TEST EVIDENCE","artifact":"results/phase1/once_only_test/summary.json","details":{"attempt_id":core05["attempt_id"],"repair_recovery_by_seed":core05_stats["seed_stability"]["frozen_receiver_l20_h5"],"no_defense_by_seed":core05_stats["seed_stability"]["no_defense"],"evaluation_rows":core05["raw_evaluation_count"],"oracle_dependent":not core05["deployable_without_oracle"]}},
        {"title":"Real Model Instrumentation","status":"VERIFIED","provenance_type":"VERIFIED PRECOMPUTED EXPERIMENT","artifact":"results/manifests/P0_mech_20261012_real_instrumentation_0.json","details":{"model":real.get("model_id"),"revision":real.get("model_revision"),"manifest_valid":True}},
        {"title":"GPT-2 IOI Calibration","status":"VERIFIED","provenance_type":"VERIFIED PRECOMPUTED EXPERIMENT","artifact":"results/calibration/ioi/summary.json","details":{"baseline_accuracy":ioi["baseline"]["accuracy"],"known_recovery":ioi["known_group"]["normalized_recovery"],"random_mean":ioi["comparison"]["control_mean_normalized_recovery"],"passive_delta":ioi["passive_non_interference"]["max_absolute_logit_difference"]}},
        {"title":"AETHER Positive Control","status":"VERIFIED LEVEL 1","provenance_type":"VERIFIED PRECOMPUTED EXPERIMENT","artifact":"results/phase1/paired_real/summary.json","details":{"development_cases":paired["counts"]["N_total"],"clean_correct":paired["counts"]["N_clean_correct"],"attack_success":paired["counts"]["N_attack_success"],"message_rescue":paired["message_interventions"]["clean_message_rescue_mean_recovery"],"full_path":paired["full_distributed_path_verified"]}},
        {"title":"Bridge Verification Protocol (BVP)","status":"LEVEL 1 ACCEPTED · FULL PATH NOT VERIFIED","provenance_type":"VERIFIED PRECOMPUTED EXPERIMENT","artifact":"results/phase1/paired_real/summary.json","details":{"accepted_claim":"mediator message causally affects outcome on the development pair","message_rescue":paired["message_interventions"]["clean_message_rescue_mean_recovery"],"full_distributed_path_verified":paired["full_distributed_path_verified"],"protocol":"docs/BVP_PROTOCOL.md"}},
        {"title":"Causal Specificity","status":"INSUFFICIENT EVIDENCE","provenance_type":"VERIFIED PRECOMPUTED EXPERIMENT","artifact":"results/phase1/causal_specificity/summary.json","details":{"surviving_candidates":len(specificity["supported_internal_causal_candidates"]),"assessment":specificity["assessment_outcome"],"message_recovery":specificity["message_only_recovery"]}},
        {"title":"Balanced V2","status":"GATE STOP — INTERNAL SCAN NOT RUN","provenance_type":"VERIFIED PRECOMPUTED EXPERIMENT","artifact":"results/phase1/balanced_v2/full_v2_1/summary.json","details":{"A_TO_B":v2["counts_by_direction"]["A_TO_B"],"B_TO_A":v2["counts_by_direction"]["B_TO_A"]}},
        {"title":"MCPTox","status":"ADAPTER/RELEASED-RESPONSE SMOKE","provenance_type":"VERIFIED PRECOMPUTED EXPERIMENT","artifact":"results/phase1/mcptox/smoke/summary.json","details":mcptox},
        {"title":"TAMAS","status":"ADAPTER SMOKE","provenance_type":"VERIFIED PRECOMPUTED EXPERIMENT","artifact":"results/phase1/tamas/smoke/summary.json","details":tamas},
        {"title":"1.5B Qualification","status":mq["result_state"],"provenance_type":"VERIFIED PRECOMPUTED EXPERIMENT","artifact":"results/phase1/model_qualification/v2_mq_hw1_retry/manifest.json","details":{"model_accessed":mq["model_accessed"],"mq_g1":mq["mq_g1"],"mq_g2":mq["mq_g2"]}},
        {"title":"Qwen SAE","status":sae["scientific_outcome"],"provenance_type":"VERIFIED REAL-MODEL NEGATIVE RESULT","artifact":"results/phase1/sae/qwen15b/summary.json","details":{"seeds":[item["seed"] for item in sae["seed_summaries"]],"epochs_per_seed":[item["epochs_completed"] for item in sae["seed_summaries"]],"selected_seed":sae["selected_seed"]}},
        {"title":"SmolLM2 Qualification","status":"FAILED QUALIFICATION","provenance_type":"VERIFIED REAL-MODEL NEGATIVE RESULT","artifact":"results/phase1/model_qualification/second_model/summary.json","details":{"model":second_model["model"]["model_id"],"clean_correct_A":second_model["behavioral"]["mq_g1"]["counts"]["clean_correct_A"],"clean_correct_B":second_model["behavioral"]["mq_g1"]["counts"]["clean_correct_B"],"instrumentation":second_model["instrumentation"]["overall"]}},
        {"title":"Real-Qwen Agent C","status":"COMPLETED WITHOUT DEMONSTRATED IMPROVEMENT","provenance_type":"VERIFIED REAL-MODEL DEVELOPMENT EVIDENCE","artifact":"results/phase1/agent_c/qwen15b/summary.json","details":{"rows":agent_c["total_rows"],"incoming_accuracy":agent_c["incoming_decision_accuracy_all_rows"],"reviewed_accuracy":agent_c["reviewed_decision_accuracy_all_rows"],"paired_difference":agent_c["paired_accuracy_difference"],"mcnemar_p":agent_c["mcnemar_exact_p_value"]}},
    ]


def system_status() -> list[dict[str, str]]:
    """Return claim-safe current capabilities."""
    return [
        {"capability":"Synthetic patient tools","status":"WORKING — DETERMINISTIC"}, {"capability":"Real MCP","status":"IMPLEMENTED — RUNTIME DEPENDENT"},
        {"capability":"Qualified Qwen model","status":"VERIFIED PASS"}, {"capability":"Live Model + MCP","status":"SEPARATE INTEGRATION PATH"},
        {"capability":"Deterministic Agent A / mediator / Agent B","status":"WORKING"},
        {"capability":"Tool-output manipulation","status":"WORKING"}, {"capability":"Paired clean/attack traces","status":"WORKING"},
        {"capability":"Clean-message rescue","status":"VERIFIED"}, {"capability":"Attacked-message induction","status":"VERIFIED"},
        {"capability":"Activation capture/intervention","status":"WORKING"}, {"capability":"Tracr calibration","status":"VERIFIED"},
        {"capability":"GPT-2 IOI calibration","status":"VERIFIED"}, {"capability":"MCPTox adapter","status":"SMOKE ONLY"},
        {"capability":"TAMAS adapter","status":"SMOKE ONLY"}, {"capability":"Internal causal localization","status":"QCI-2 SUPPORTED — COMPLETE DCMG NOT CLAIMED"},
        {"capability":"Balanced V2 causal search","status":"VERIFIED COMPLETE"}, {"capability":"1.5B qualification","status":"VERIFIED PASS"},
        {"capability":"Held-out validation","status":"VERIFIED ACCEPTED"}, {"capability":"Held-out test","status":"VERIFIED ACCEPTED — ONCE-ONLY CLOSED"},
        {"capability":"Qwen SAE extension","status":"COMPLETED - REJECTED BY FROZEN GATES"},
        {"capability":"Second-model qualification","status":"COMPLETED - FAILED BALANCED TASK GATE"},
        {"capability":"Agent C development study","status":"COMPLETED - NO IMPROVEMENT DEMONSTRATED"},
        {"capability":"Real-Qwen red team","status":"FAILED ATTEMPT RETAINED - NO EVIDENCE CLAIM"},
    ]
