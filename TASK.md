# AETHER current bounded task

## DCAP-1 portability repair and rerun

Retain the failed first development-capture archive. Repair the qualified-token
replay without changing cases, model, components, metrics, or split policy;
test the padded-input reconstruction; pin a regenerated notebook to the repair
commit; and rerun DCAP-1 once. Do not treat the failed archive as activation
evidence or proceed to component selection.

## Prospective Qwen development activation capture — 2026-11-11

Following IA-G1 PASS, freeze a development-only capture protocol before any
broad internal activation data are observed. Exclude the four IA-G1 cases from
component selection. Use 16 fixed eligible cases for discovery capture and four
remaining eligible cases as an untouched development audit cohort. Capture
sender and receiver attention/MLP outputs and pre-`o_proj` heads at every Qwen
layer for clean and attacked prompts, retaining exact prompts, token IDs,
component identities, tensor hashes, model revision, and seed.

This task may compute declared paired activation-difference measurements but
must not execute causal search, choose a circuit, tune on the audit cohort,
access validation/test, or claim localization. Its output feeds a separately
frozen intervention and negative-control protocol.

## Qwen2.5-1.5B instrumentation acceptance on Kaggle — 2026-11-11

Ingest and hash-verify the successful MQ-HW1/MQ-G1/MQ-G2 qualification bundle,
then prospectively freeze and prepare IA-G1 before any instrumentation result is
observed. IA-G1 uses the same pinned Qwen revision, CPU float32 execution, and a
fixed balanced subset of eligible development cases. It verifies passive hook
non-interference, activation persistence, the exact pre-`o_proj` head tensor,
hook cleanup, and fixed clean-to-attacked activation-patch execution.

Do not rank components, scan layers/heads, tune from observed effects, run search
or RL, claim a circuit, evaluate remediation, or access validation/test. IA-G1
PASS authorizes only review of a later prospective development capture and
intervention protocol. Any failure is retained and stops instrumentation work.

Acceptance: the qualification bundle and all manifest-listed artifacts verify;
the IA config is machine-readable and frozen; model-free tests pass; an
uploadable one-attempt Kaggle notebook runs preflight before snapshot access;
every output and activation artifact is hashed; failures remain visible.

## Real Qwen2.5-1.5B qualification on Kaggle — 2026-11-10

Portability repair: Kaggle's Git checkout normalizes text files to LF while
Windows checkouts can use CRLF. The runner verifies frozen hashes across
newline-only conversions, still rejects content changes, and records canonical
LF hashes plus diagnostics. Regenerate and use the notebook pinned to the fixed
runner commit. The reported failure happened before hardware/model access.

Prepare an executable Kaggle path for the already approved MQ-HW1/MQ-G1/MQ-G2
campaign. Pin the official immutable Qwen2.5-1.5B-Instruct revision, run the
CPU-float32 pre-access hardware gate before model download, implement a
single-attempt development-only qualification runner with full raw outputs,
and provide a clean uploadable notebook. MQ-G2 runs only after MQ-G1 passes.
Do not run activation capture/interventions, open validation/test, change the
frozen thresholds/prompts/cases, or describe qualification as causal-circuit
evidence. Stop after MQ-G2 and report whether a separate instrumentation stage
is authorized by the frozen protocol.

Acceptance: notebook and runner are syntax-valid; model-free checks pass; case,
control, and V2.1 hashes match the frozen MQ-G1 config; the snapshot is pinned
and hashed; every failure is retained; no model is loaded outside Kaggle; the
repository suite is run. Remote CPU resource availability and actual Qwen gate
outcomes require the user's Kaggle execution.

## Kaggle notebook reliability repairs — 2026-11-10

Repair the uploadable notebook against observed Linux setup failures. Include pip,
Linux-compatible demo dependencies, Agg rendering, persistent test logs and
JUnit output, isolated temporary runtime storage, synthetic PPO training and
hashed exports. Validate notebook cell execution locally where possible and run
the repository suite. Remote CUDA execution remains to be verified on Kaggle.

## Graph-aware hierarchical RL hardening — 2026-11-05

Add an additive AETHER-specific constrained search environment whose actions
explicitly encode operation, sender/message/receiver/bridge region, target and
intervention operator. The policy must consume DCMG adjacency, node/edge type
features, current causal measurements, remaining budget and the complete bounded
query ledger. Support node pruning/intervention, explicit edge cuts and stop;
preserve the existing flat PPO as a baseline. Verify behavior on branching
synthetic graphs only. This is methodological hardening under N2, not permission
to claim PPO or RL circuit discovery as new, alter frozen contracts, access
locked splits, load a model, or fabricate research evidence.

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
