# QCI-2 matched-search and BVP method proposal — review request

**State:** `AWAITING_HUMAN_REVIEW`

**Proposal:** `configs/phase1_core/qci2_method_freeze_v1.yaml`

## Decision requested

Approve, reject, or request a prospective revision of the proposal before any
new evidence-bearing model execution. Approval must record reviewer identity,
UTC timestamp, exact proposal SHA-256, decision and comments. This document is
not itself an approval and does not satisfy the completion gate.

## Frozen design summary

- Uses exactly the four independently replicated QCI-2 internal candidates.
- Uses the 16 development-discovery cases only; four development-audit cases,
  validation and test are prohibited for tuning and selection.
- Treats every graph edge as hypothesized until its own intervention evidence
  passes.
- Separates sender→message, message→receiver and receiver→outcome tests.
- Compares matched random, greedy, beam, receiver-only and flat PPO; hierarchical
  PPO is secondary and cannot replace the flat baseline.
- Gives each method/seed a fresh cache and identical unique-mask/forward limits.
- Reports signed faithfulness, benign damage, footprint, costs, stability,
  invalid/errors and wall time separately.
- Claims at most one-step local minimality after all single removals are tested.
- Preserves the decision-code-copying construct limitation and requires any
  conflicting-evidence task to be a distinct prospective study.

## Reviewer checklist

- [ ] Candidate identity is independent of audit effect-size optimization.
- [ ] Audit, validation and test cases cannot enter method tuning.
- [ ] Budgets are comparable and include all uncached model forwards.
- [ ] Required negative controls are scientifically meaningful.
- [ ] BVP edges cannot be promoted from association or graph topology.
- [ ] Flat PPO checkpoint reload and deterministic inference are required.
- [ ] Benign utility is measured separately from identity non-interference.
- [ ] Claim boundary is acceptable.
- [ ] Construct-validity limitation is explicit.

## Reviewer decision

Intentionally blank. A human reviewer must complete a separate immutable
decision artifact after reviewing the exact proposal hash.
