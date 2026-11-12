# AETHER project state

## 2026-11-12 QCI-2 prospectively frozen — semantic-control correction

QCI-1.1 remains a valid negative result for **case-specific** mediation: its
same-direction shuffled donor changed case identity but preserved the clean and
attacked decision semantics. Every `A_TO_B` discovery case has clean decision A
and attacked decision B, while every `B_TO_A` case has the reverse. The QCI-1
control therefore could not test decision semantics shared across cases.

Before any QCI-2 model execution, the repository now freezes a distinct study,
reusing all 12 QCI-1 candidates without reselection. It requires paired effects,
same-decision generalization, opposite-decision contrast, position specificity,
and identity/passive non-interference. Audit, validation and test remain closed.

The local preflight verified all frozen inputs and correctly blocked before
model access because only 2.91 GiB RAM was available. The first Kaggle upload
stopped in model-free tests before preflight and model access because the clean
checkout omitted gitignored QCI-1 console logs recorded in the original archive
inventory. The verifier now permits only absent `.log` entries while continuing
to require and hash every scientific artifact. A corrected, repinned notebook
must run once. QCI-2 cannot retroactively change the QCI-1 result.

## 2026-11-12 QCI-1.1 verified negative result — stop internal causal claim

The retained Kaggle QCI-1.1 archive passed independent verification and was
atomically ingested under `results/phase1/causal_interventions/qwen15b_qci1`.
All 1,344 candidate/control executions and 32 whole-message controls completed
with zero invalid/error rows; the query ledger remained within budget and
development-audit, validation and test executions were zero. None of the 12
prospectively selected candidates passed every frozen support predicate.

Several receiver candidates produced large rescue and induction effects, but
the effects did not separate from shuffled-source controls. They are therefore
non-specific replacement effects, not supported causal mediators under the
frozen protocol. The binding next state is `STOP_NO_SUPPORTED_CANDIDATE`.
QCI-A1 must not run, and the present Qwen internal-circuit, matched-search,
mechanism-guided remediation and locked causal-evaluation path stops. This is a
valid negative scientific result, but it does not establish AETHER's required
N1 internal cross-agent circuit claim.

## 2026-11-11 BFCL package compatibility verified

The pinned `bfcl_eval==2026.3.23` and `agentdojo==0.1.35` wheel interfaces were
inspected without downloading benchmark data. AgentDojo's declared CLI is
compatible. BFCL exposes a reusable Qwen function-calling handler, but its
registry does not contain the frozen Qwen2.5-1.5B primary model. A minimal
disclosed registry adapter now delegates to BFCL's handler and evaluator while
requiring the already-qualified immutable model snapshot and verifying every
snapshot file hash. This future result must be labelled “official evaluator
with disclosed AETHER model adapter,” not an unmodified leaderboard model.
Neither benchmark has executed and no score exists.

## 2026-11-11 Tracr known-structure intervention PASS

The pinned Tracr reverse program now has an executed causal calibration rather
than structure-only metadata. Before observing outcomes, all eight compiled
attention/MLP half-layers were frozen as an exhaustive zero-parameter ablation
set over three exact reverse cases. All baseline, passive-copy and restored
outputs were exact; 15 of 24 target/case ablations changed a non-BOS output;
all targets executed; validation/test executions were zero. The accepted clean
run is under `results/calibration/tracr_intervention`; the earlier structure-
only result and an incomplete-manifest first intervention attempt are retained
separately.

A machine-readable 20-gate Phase-1 completion audit now prevents partial
software or narrative status from being reported as project completion. After
QCI ingestion, six gates pass, the conditional QCI audit is not applicable and
thirteen required artifacts remain absent.

## 2026-11-11 QCI-1.1 runner ready for Kaggle execution

The real discovery-only intervention runner and commit-pinned Kaggle notebook
are implemented. The runner covers 64 selected-source captures, 1,344
candidate/control executions, 32 whole-message controls, exact sender/message/
receiver provenance, raw invalid/error denominators, query budgets, immutable
support classification and zero development-audit/validation/test access. Its
real preflight verified every input hash and candidate locally, then correctly
blocked before model access because only 2.69 GiB RAM was available. Kaggle must
execute `notebooks/aether_qwen_causal_interventions_cpu.ipynb`; no causal
candidate is accepted until that retained run is verified.

The runner is hardened at source commit
`0e8a616aedd8a7a5caf2af5b34d9170bf9f114fc`: every successful active patch
must apply exactly once and failures retain a reproducibility manifest. The
uploadable notebook is regenerated at `dbfc837` and pins that immutable source.
A strict atomic ingestion command verifies hashes, denominators, controls,
budgets and split locks before admitting the downloaded bundle. It refuses
overwrites, symlinks and ambiguous artifact names.

The conditional QCI-A1 development audit is also prospectively frozen before
the discovery result is available. It may run only when the verified discovery
gate reports supported candidates. To preserve the pre-existing 240-execution
audit budget, it audits at most eight supported candidates ordered by the
already-frozen activation score: 224 candidate executions plus eight whole-
message controls. The four untouched development-audit cases are fixed; an
immutable-source Kaggle notebook and strict result verifier are prepared.

## 2026-11-11 QCI-1 candidate selection complete

After committing protocol SHA-256
`8a4712ef3160251ed24dd8d82eaee005140e2853beddef88c9991e1e991c704e`,
the discovery-only selector hash-verified and opened exactly 64 discovery
activation artifacts. It did not open development-audit tensors, validation, or
test. From 784 expanded sender/receiver module and head candidates, the frozen
bidirectional rule selected 12 candidates for causal intervention. These are
correlational prefilter results only; none is a causal component until it passes
paired intervention and specificity controls.

## 2026-11-11 DCAP-1 PASS

The corrected development-capture run passed all seven frozen predicates on the
20 declared development cases. It produced 80 sender/receiver clean/attacked
activation artifacts and 3,360 layer-level paired measurements. All artifact,
manifest, and archive-content hashes verified locally; qualified predictions
were reproduced; hooks were removed; measurements were finite; and validation
and test execution counts remained zero. The 4.87 GB tensor archive remains
external under SHA-256
`7890212a8e7a4eb099be86bc572cd6172fd1c45b839f695e56e6ba4a46e97b21`.
This authorizes prospective causal-intervention protocol review only.

## 2026-11-11 DCAP-1 first attempt retained as failed

The development-capture preflight and pinned model download passed, but capture
stopped before producing activation evidence. Qualification stored exact
left-padded batch token IDs, while the first DCAP runner compared those IDs to
an individually tokenized, unpadded prompt. The runner now verifies the
non-padding prompt tokens and replays the exact qualified input IDs and
attention mask. A fresh run with the corrected, commit-pinned notebook is
required; the failed archive is not activation or circuit evidence.

**Current checkpoint:** model-independent Phase 1 implementation, 2026-11-04
**Development branch:** `lm`

## 2026-11-11 Qwen 1.5B IA-G1 PASS

The prospective Kaggle instrumentation-acceptance gate passed all nine
predicates. Eight passive checks had exact zero logit difference; the layer-14
pre-`o_proj` tensor reconstructed as 12 heads by 128 dimensions; all 73 saved
activation tensors round-tripped exactly; both fixed directional activation
patches applied once with nonzero effects; every hook was removed; and
validation/test executions remained zero. All archive and manifest hashes were
reverified locally. This authorizes only a prospective development capture
protocol, not circuit or remediation claims.

## 2026-11-11 qualified Qwen 1.5B checkpoint

The single authorized Kaggle campaign passed MQ-HW1, MQ-G1, and MQ-G2 on the
24-case development cohort. All 24 clean decisions were correct, all 24 attacks
reached their predefined outcome, both directions had 12 eligible pairs, all
mediators were valid, message rescue/induction were 12/12 per direction, and
validation/test execution counts were zero. All eleven manifest-listed inner
artifacts were rehashed successfully during local ingestion under
`results/phase1/model_qualification/qwen15b_kaggle_20261110`.

This is behavioral and message-causal qualification, not internal circuit
evidence. The next bounded stage is prospectively frozen IA-G1 instrumentation
acceptance: passive non-interference, selected activation capture, pre-`o_proj`
head semantics, persistence, cleanup, and fixed intervention execution on
development examples only. Circuit localization/search remains closed until
IA-G1 executes and passes.

## 2026-11-10 Kaggle Qwen preflight newline portability

The Kaggle preflight rejection was caused by Git converting committed text files
from CRLF to LF while the frozen hashes had been recorded on Windows. The
qualification runner now verifies each frozen hash against raw, canonical LF,
and canonical CRLF bytes. Any content change still fails closed. Reproducibility
manifests use canonical LF hashes and record the observed hash forms. Updated
the generated Kaggle notebook to pin the resulting runner source. This is a
software compatibility fix only; the traceback occurred before hardware
preflight or model access, so it is not Qwen qualification evidence.

## Implemented

- Deterministic two-agent and Agent C paths, attack corpus, MCP SDK boundary,
  red-team orchestration, review demo and manifest-backed synthetic runs.
- Cross-agent graphs, frozen causal metrics, residual/head/SAE/message
  interventions, repeated-call multi-mediator replay and explicit edge cuts.
- Qwen attention capture/intervention at pre-`o_proj`, with layer/head mapping.
- Greedy, beam, matched-random, receiver-only, full cross-agent and PPO search.
  PPO now observes the complete bounded query ledger and its saved policy passes
  the synthetic acceptance task.
- An additive graph-aware hierarchical PPO environment factorizes operation,
  region, target and operator actions over explicit DCMG adjacency. It supports
  node interventions, bridge/internal edge cuts and stop under one query budget,
  with a separately identified deterministic local-repair phase. Three-seed
  branching-graph acceptance is synthetic software evidence only.
- Trained-SAE NPZ loading with hashes, model/component provenance,
  normalization metadata and reconstruction gates.
- A measured evaluator joining intervention executions to search while retaining
  the fixed cohort, raw outputs and forward-pass costs.
- Paired statistics, bootstrap CIs, McNemar tests, seed stability, invalid/error
  denominators, controls, and manifest-gated JSON/CSV/plot reports.
- BFCL/AgentDojo command plans and proposed pins, strict result imports,
  MCPTox/TAMAS preparation, frozen development config, transfer preflight,
  Python 3.11 CI and artifact/evidence guards.

## Verification

Python 3.11.9: **401 passed, 5 skipped** at the QCI-2 portability checkpoint
(382 unit plus 19 integration/regression passes).
The gated skips are two real-Qwen
tests, one pinned GPT-2 test, and two opt-in demo artifact tests. Regression
coverage runs the P1, P2, P3, P4 and end-to-end smokes.

## Evidence boundary and remaining work

Toy, fixture, rule-based and synthetic runs are software acceptance, not Qwen or
benchmark evidence. No locked validation/test split was opened. Qwen2.5-1.5B
qualification, instrumentation acceptance and development activation capture
have passed. The immediate unresolved scientific gate is the frozen QCI-2
decision-semantic discovery run on Kaggle. QCI-1.1 is already a verified
negative result and its audit is forbidden. QCI-2 determines whether a distinct
development-only semantic-mediation claim can proceed to a separately frozen
audit. Later work still requires approved development-audit,
method-freeze review, validation and once-only test evaluation; official
benchmarks, real SAE/red-team/Agent C evidence and a second qualified model also
remain absent.

Known-structure Tracr intervention calibration and GPT-2 IOI causal calibration
now both pass. They validate intervention machinery on calibration substrates;
they do not substitute for QCI-2 or establish an AETHER internal circuit.

The transfer config deliberately has `revision: pending`, so preflight blocks
until an immutable revision is reviewed. Proposed BFCL/AgentDojo pins and task
scopes likewise require official-package compatibility confirmation.
