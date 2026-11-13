"""Model-independent tests for the approved CORE-02 planner."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from causal.core_search import build_run_plans, enumerate_legal_masks, load_effective_method_freeze


ROOT = Path(__file__).resolve().parents[2]
PROPOSAL = ROOT / "configs/phase1_core/qci2_method_freeze_v2.yaml"
V2_1_AMENDMENT = ROOT / "configs/phase1_core/qci2_method_freeze_v2_1_amendment.yaml"
AMENDMENT = ROOT / "configs/phase1_core/qci2_method_freeze_v2_2_amendment.yaml"
PROPOSAL_DECISION = ROOT / "results/phase1/method_freeze/decision.json"
AMENDMENT_DECISION = ROOT / "results/phase1/method_freeze/amendment_v2_2_decision.json"


def _freeze():
    return load_effective_method_freeze(
        repo=ROOT, proposal_path=PROPOSAL, amendment_path=AMENDMENT,
        v2_1_amendment_path=V2_1_AMENDMENT,
        proposal_decision_path=PROPOSAL_DECISION,
        amendment_decision_path=AMENDMENT_DECISION,
    )


def test_effective_method_requires_exact_human_approved_hashes(tmp_path: Path) -> None:
    changed = json.loads(AMENDMENT_DECISION.read_text(encoding="utf-8"))
    changed["amendment_sha256"] = "0" * 64
    decision = tmp_path / "decision.json"
    decision.write_text(json.dumps(changed), encoding="utf-8")
    with pytest.raises(ValueError, match="approval hash differs"):
        load_effective_method_freeze(
            repo=ROOT, proposal_path=PROPOSAL, amendment_path=AMENDMENT,
            v2_1_amendment_path=V2_1_AMENDMENT,
            proposal_decision_path=PROPOSAL_DECISION, amendment_decision_path=decision,
        )


def test_every_legal_overlap_safe_mask_is_enumerated() -> None:
    masks = enumerate_legal_masks(_freeze().proposal)
    assert len(masks) == 36
    assert () in masks
    assert not any({"message.decision_code", "message.whole"}.issubset(mask) for mask in masks)
    assert not any({
        "receiver.head.L22.H7.pre_o_proj", "receiver.module.L22.attention_output"
    }.issubset(mask) for mask in masks)


def test_plans_are_matched_and_cache_isolated_per_method_seed() -> None:
    plans = build_run_plans(_freeze())
    assert len(plans) == 15
    assert len({plan.cache_namespace for plan in plans}) == 15
    assert {plan.maximum_model_forward_steps for plan in plans} == {7360}
    assert {plan.model_forwards_per_mask_evaluation for plan in plans} == {160}
    assert {plan.case_ids for plan in plans} == {tuple(_freeze().proposal["case_ids"])}


def test_unfrozen_seed_and_method_fail_closed() -> None:
    freeze = _freeze()
    with pytest.raises(ValueError, match="outside the frozen seed"):
        build_run_plans(freeze, seeds=[44])
    with pytest.raises(ValueError, match="unknown method"):
        build_run_plans(freeze, methods=["new_search"])
