# QCI-2 matched-search/BVP method proposal v2 — scientific review package

**Candidate:** `configs/phase1_core/qci2_method_freeze_v2.yaml`

**State:** `AWAITING_HUMAN_REVIEW`

This file is a checklist, not an approval record. A human reviewer must bind any
decision to the exact v2 SHA-256 printed by `python -m causal.method_freeze`.

## Required decision checks

- [ ] Retained/removed node semantics describe executable real-model operations.
- [ ] Sender → message → receiver ordering and donor identities are unambiguous.
- [ ] Whole-message/field and layer/head overlaps are correctly prohibited.
- [ ] Edges cannot be promoted by topology, association or placeholder scores.
- [ ] Per-method/per-seed limits and every reserved accounting phase are fair.
- [ ] PPO cached actions, training, selection, reload and verification are logged.
- [ ] Exhaustion remains `INCOMPLETE_BUDGET` and cannot imply minimality.
- [ ] Raw-logit non-interference is not mislabelled benign utility.
- [ ] Each edge has testable intervention, measurement, controls and thresholds.
- [ ] Receiver-edge tests preserve incoming bytes exactly where required.
- [ ] A connected path requires all of its edge records to pass.
- [ ] The construct-validity stress test is separate and remains unexecuted.
- [ ] QCI-1/QCI-2 artifacts and all protected splits remain unchanged.

## Human decision

Intentionally absent. The implementation agent must not generate or sign the
method-freeze decision.
