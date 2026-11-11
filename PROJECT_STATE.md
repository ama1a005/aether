# AETHER project state

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

Python 3.11.9: **352 passed, 5 skipped** as of the DCAP-1 notebook checkpoint.
The gated skips are two real-Qwen
tests, one pinned GPT-2 test, and two opt-in demo artifact tests. Regression
coverage runs the P1, P2, P3, P4 and end-to-end smokes.

## Evidence boundary and remaining work

Toy, fixture, rule-based and synthetic runs are software acceptance, not Qwen or
benchmark evidence. No locked validation/test split was opened. The larger
computer must: pin Qwen2.5-1.5B; pass preflight and qualification; run real hook,
capture, intervention, multi-seed, SAE, red-team and Agent C experiments; execute
official benchmarks; qualify a second model; then freeze the method before
approved validation and once-only test evaluation.

The transfer config deliberately has `revision: pending`, so preflight blocks
until an immutable revision is reviewed. Proposed BFCL/AgentDojo pins and task
scopes likewise require official-package compatibility confirmation.
