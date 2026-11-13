# CORE-00 repository and evidence audit

**Date:** 2026-11-13

**Branch:** `phase1/core-nov19`

**Base/initial HEAD:** `00846b020b685dfa3ab89bce2c5227d2810c9d1e`

## Verified evidence

- Python is 3.11.9.
- QCI-2 discovery independently verifies: 1,920 candidate executions, 32
  message controls, zero invalid/errors, four supported candidates, zero
  validation/test access.
- QCI-2A1 independently verifies: 160 candidate executions, eight message
  controls, all four candidates supported, zero invalid/errors, zero
  validation/test access, next state `READY_FOR_QCI2_METHOD_FREEZE_REVIEW`.
- The full model-independent test collection executed: 409 passed, 5 skipped.
- Completion audit remains honest: 8 PASS, 1 NOT_APPLICABLE, 13 MISSING.

## Four verified internal candidates

1. `sender.module.L22.attention_output`
2. `receiver.module.L22.attention_output`
3. `receiver.head.L20.H5.pre_o_proj`
4. `receiver.head.L22.H7.pre_o_proj`

## File-by-file causal risks

- `causal/bridge/message_bridge.py` creates arbitrary association scores from
  absolute activation differences multiplied by 0.1. It has no production call
  site. It is now explicitly labelled synthetic association scaffolding and is
  ineligible for scientific evidence.
- `causal/candidate_graph/builder.py` creates placeholder bridge edges from the
  first node in each region. These are hypotheses only and must not enter a
  final evidence graph as supported edges.
- `causal/evidence.py` correctly requires intervention evidence for supported
  edges, but existing QCI-2 rows support individual semantic interventions, not
  an independently verified connected sender→message→receiver→outcome path.
- `docs/PHASE1_METHOD_FREEZE_CANDIDATE.md` is the historical failed Qwen-0.5B
  candidate. It is not the QCI-2 method freeze.
- Existing search code is model-independent and measured-evaluator compatible,
  but no retained real-Qwen matched comparison exists.

## Construct-validity warning

The qualified sender is instructed to output the tool `recommendation_code` and
the receiver is instructed to return the serialized sender `decision_code`.
QCI-2 therefore supports decision-semantic mediation under this positive-control
task, but it may reflect copying/representing a decision token rather than a
richer unsafe-trust computation. QCI-2 remains valid and immutable. A genuine
conflicting-evidence stress test must be a separate prospectively frozen study.

## Missing core dependencies

1. Independent human review of the new QCI-2 method proposal.
2. Real-Qwen evaluator/runner for matched search with isolated method caches.
3. Per-edge BVP evidence linking sender intervention to regenerated message,
   message intervention to receiver state/outcome, and receiver intervention to
   outcome with identical incoming bytes.
4. Development remediation comparison with benign utility and full Pareto data.
5. Locked validation and once-only test, which remain forbidden until prior
   gates are frozen, executed and reviewed.

## Next gate

Review `configs/phase1_core/qci2_method_freeze_v1.yaml`. It intentionally remains
`AWAITING_HUMAN_REVIEW`; no completion result or `decision_recorded: true` file
has been created. After independent approval, pin its exact SHA-256 and build the
commit-pinned development-only runner without using audit cases for tuning.
