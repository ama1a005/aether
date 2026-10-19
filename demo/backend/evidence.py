"""Read-only adapters for committed scientific evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _read(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def evidence_cards() -> list[dict[str, Any]]:
    """Return concise cards computed from actual committed artifacts."""
    real = _read("results/manifests/P0_mech_20261012_real_instrumentation_0.json")
    ioi = _read("results/calibration/ioi/summary.json")
    paired = _read("results/phase1/paired_real/summary.json")
    specificity = _read("results/phase1/causal_specificity/summary.json")
    v2 = _read("results/phase1/balanced_v2/full_v2_1/summary.json")
    mcptox = _read("results/phase1/mcptox/smoke/summary.json")
    tamas = _read("results/phase1/tamas/smoke/summary.json")
    mq = _read("results/phase1/model_qualification/v2_mq_hw1_retry/manifest.json")
    return [
        {"title":"Real Model Instrumentation","status":"VERIFIED","provenance_type":"VERIFIED PRECOMPUTED EXPERIMENT","artifact":"results/manifests/P0_mech_20261012_real_instrumentation_0.json","details":{"model":real.get("model_id"),"revision":real.get("model_revision"),"manifest_valid":True}},
        {"title":"GPT-2 IOI Calibration","status":"VERIFIED","provenance_type":"VERIFIED PRECOMPUTED EXPERIMENT","artifact":"results/calibration/ioi/summary.json","details":{"baseline_accuracy":ioi["baseline"]["accuracy"],"known_recovery":ioi["known_group"]["normalized_recovery"],"random_mean":ioi["comparison"]["control_mean_normalized_recovery"],"passive_delta":ioi["passive_non_interference"]["max_absolute_logit_difference"]}},
        {"title":"AETHER Positive Control","status":"VERIFIED LEVEL 1","provenance_type":"VERIFIED PRECOMPUTED EXPERIMENT","artifact":"results/phase1/paired_real/summary.json","details":{"development_cases":paired["counts"]["N_total"],"clean_correct":paired["counts"]["N_clean_correct"],"attack_success":paired["counts"]["N_attack_success"],"message_rescue":paired["message_interventions"]["clean_message_rescue_mean_recovery"],"full_path":paired["full_distributed_path_verified"]}},
        {"title":"Bridge Verification Protocol (BVP)","status":"LEVEL 1 ACCEPTED · FULL PATH NOT VERIFIED","provenance_type":"VERIFIED PRECOMPUTED EXPERIMENT","artifact":"results/phase1/paired_real/summary.json","details":{"accepted_claim":"mediator message causally affects outcome on the development pair","message_rescue":paired["message_interventions"]["clean_message_rescue_mean_recovery"],"full_distributed_path_verified":paired["full_distributed_path_verified"],"protocol":"docs/BVP_PROTOCOL.md"}},
        {"title":"Causal Specificity","status":"INSUFFICIENT EVIDENCE","provenance_type":"VERIFIED PRECOMPUTED EXPERIMENT","artifact":"results/phase1/causal_specificity/summary.json","details":{"surviving_candidates":len(specificity["supported_internal_causal_candidates"]),"assessment":specificity["assessment_outcome"],"message_recovery":specificity["message_only_recovery"]}},
        {"title":"Balanced V2","status":"GATE STOP — INTERNAL SCAN NOT RUN","provenance_type":"VERIFIED PRECOMPUTED EXPERIMENT","artifact":"results/phase1/balanced_v2/full_v2_1/summary.json","details":{"A_TO_B":v2["counts_by_direction"]["A_TO_B"],"B_TO_A":v2["counts_by_direction"]["B_TO_A"]}},
        {"title":"MCPTox","status":"ADAPTER/RELEASED-RESPONSE SMOKE","provenance_type":"VERIFIED PRECOMPUTED EXPERIMENT","artifact":"results/phase1/mcptox/smoke/summary.json","details":mcptox},
        {"title":"TAMAS","status":"ADAPTER SMOKE","provenance_type":"VERIFIED PRECOMPUTED EXPERIMENT","artifact":"results/phase1/tamas/smoke/summary.json","details":tamas},
        {"title":"1.5B Qualification","status":mq["result_state"],"provenance_type":"VERIFIED PRECOMPUTED EXPERIMENT","artifact":"results/phase1/model_qualification/v2_mq_hw1_retry/manifest.json","details":{"model_accessed":mq["model_accessed"],"mq_g1":mq["mq_g1"],"mq_g2":mq["mq_g2"]}},
    ]


def system_status() -> list[dict[str, str]]:
    """Return claim-safe current capabilities."""
    return [
        {"capability":"Synthetic patient tools","status":"WORKING — DETERMINISTIC"}, {"capability":"Real MCP stdio demo","status":"IMPLEMENTED — INSTALL/PROTOCOL CHECK BLOCKED"},
        {"capability":"Qwen 0.5B demo inference","status":"IMPLEMENTED — GPU QUALIFICATION NOT RUN"}, {"capability":"Deterministic Agent A / mediator / Agent B","status":"WORKING"},
        {"capability":"Tool-output manipulation","status":"WORKING"}, {"capability":"Paired clean/attack traces","status":"WORKING"},
        {"capability":"Clean-message rescue","status":"VERIFIED"}, {"capability":"Attacked-message induction","status":"VERIFIED"},
        {"capability":"Activation capture/intervention","status":"WORKING"}, {"capability":"Tracr calibration","status":"VERIFIED"},
        {"capability":"GPT-2 IOI calibration","status":"VERIFIED"}, {"capability":"MCPTox adapter","status":"SMOKE ONLY"},
        {"capability":"TAMAS adapter","status":"SMOKE ONLY"}, {"capability":"Internal DCMG localization","status":"INSUFFICIENT EVIDENCE"},
        {"capability":"Balanced V2 internal scan","status":"NOT RUN — GATE STOP"}, {"capability":"1.5B qualification","status":"BLOCKED BY LOCAL MEMORY"},
        {"capability":"Held-out validation","status":"NOT OPENED"}, {"capability":"Held-out test","status":"NOT OPENED"},
    ]
