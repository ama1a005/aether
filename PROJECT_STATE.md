# AETHER project state

**Current checkpoint:** model-independent Phase 1 implementation, 2026-11-04
**Development branch:** `lm`

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

Python 3.11.9: **333 passed, 5 skipped**. The gated skips are two real-Qwen
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
