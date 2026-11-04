# AETHER current bounded task

## Model-independent Phase 1 completion — 2026-11-04

Implement and verify every Phase 1 component that does not require loading the
qualified model or downloading benchmark data: generalized path replay, Qwen
pre-projection adapters, trained-SAE interfaces, measured search, fully observed
PPO, statistics/reporting, benchmark preparation, development configuration,
transfer preflight and CI guards.

Constraints: do not change contracts, download models/data, open validation/test,
fabricate results, hide errors, or treat synthetic acceptance as scientific
evidence. Preserve raw errors in denominators. Future pushes target `lm`.

Acceptance: complete Python suite and smokes pass; config/artifact validation
passes; public interfaces are tested and fail closed; documentation separates
code, executed evidence and future work.

Next bounded task: on the larger computer, select an immutable Qwen2.5-1.5B
revision, install the exact environment, run `python scripts/phase1_preflight.py`,
and stop unless every gate passes. Model qualification requires a separate task.
