# TASK.md — AETHER Sprint Task Board

## Current bounded task — Phase 1 search baseline completion on lm

User authorization: continue Phase1Project.md; all future pushes target `lm`.
Scope: additive budgeted greedy/beam search, typed matched-random controls and
receiver-only scope in `discovery/`; synthetic acceptance runner/config with
automatic manifests; substantive unit/integration tests; completion ledger.
Acceptance: strict query budget, deterministic tie-breaking and random seeds,
finite evaluation validation, cache isolation, honest local-minimality status,
raw outputs/costs retained, locked test rejected, manifest hashes verified.
Follow-on bounded scope: strict tri-location Pareto selection from supplied
validation measurements in `remediation/selector/frontier.py`, with feasibility,
cohort consistency, cost and missing-data tests. This supplies selection code;
it does not authorize reading or executing locked validation/test examples.
Correct any confirmed shared-metric implementation mismatch with the frozen
formula, while preserving original recorded results and documenting the correction.
The failed balanced-model gate and frozen MQ-HW1 threshold remain binding.
Do not access held-out cases or launch unqualified internal model experiments.
Preserve frozen contracts and historical results. Run unit/integration/regression
checks and the new synthetic acceptance command before committing on `lm`.

Follow-on bounded task: implement the mandatory NARCBench-style correlational
linear-probe baseline as reusable evaluation code. Require disjoint sample IDs,
development-only fitting by default, train-only standardization, deterministic
L2 logistic fitting, AUROC/PR-AUC, constant-feature safety, and seeded label
permutation controls. Do not load activations or execute validation/test here.

## Current bounded task — mandatory Phase 1 RL search baseline

User direction: every feature previously labelled optional in Phase 1 is now a
must-build deliverable. Phase 2 scope remains deferred. Implement RL first as a
reproducible comparison method; the frozen contract still forbids claiming RL
itself as novel.

Build a typed sender/message/receiver pruning environment with a stop action,
strict global intervention-query accounting, raw query retention, deterministic
seeding, explicit reward components, and development/synthetic-only split locks.
Implement a dependency-free PyTorch PPO actor-critic with masked categorical
actions, clipped objective, value loss, entropy term, gradient clipping, and
finite-value checks. Compare PPO with random, greedy, and beam on the same mock
candidate graph and evaluator under declared budgets. Add reward ablations,
unit/integration tests, an automatic run manifest, and honest convergence/cost
reporting. Do not access a model, validation data, or test data in this task.

After the RL checkpoint, convert the remaining former Phase 1 optional items to
mandatory scheduled deliverables: path/residual/head/SAE interventions, implicit
preference manipulation, AgentDojo, Agent C, red-team orchestration, and the
external benchmark summary. Each receives its own bounded implementation task.

## Historical task — reliability verification (2026-10-21)

Repair reproducible demo/runtime defects, verify external MCP and all twelve demo cases, run existing tests and smoke checks, and document unresolved limits. No new research experiments, benchmark downloads, or frozen-contract changes. Preserve historical artifacts.

## Historical task — real demo runtime (2026-10-19)

Resolve live-demo dependencies through a verified online or offline wheelhouse, then run CUDA, MCP, pinned-model, single-case, rescue, and 12-case acceptance in fail-fast order. Do not modify the research environment or claim live readiness before every gate succeeds.

**Sprint:** 4 Oct – 8 Oct 2026  
**Review:** 8 October 2026  
**Updated:** 2026-10-08 22:50 IST

---

## Sprint Status

| # | Task | Owner | Status | Blocker |
|---|------|-------|--------|---------|
| 1 | Shared contracts v0.1.0 | All | **DONE** | — |
| 2 | 10 fixture JSON files | All | **DONE** | — |
| 3 | RESEARCH_CONTRACT.md | All | **DONE** | — |
| 4 | AGENTS.md | All | **DONE** | — |
| 5 | benchmarks/REGISTRY.yaml | P2 | **DONE** | — |
| 6 | conftest.py | All | **DONE** | — |
| 7 | P1 two-agent target harness | P1 | **DONE** | — |
| 8 | P1 `python -m target.runner ...` demo | P1 | **DONE** | — |
| 9 | P2 attack corpus (3 families × 5) | P2 | **DONE** | — |
| 10 | P2 `python -m attacks.runner ...` demo + ASR plot | P2 | **DONE** | — |
| 11 | P3 activation hooks (non-interference) | P3 | **DONE** | — |
| 12 | P3 ZeroAblation / MeanAblation / ActivationPatch | P3 | **DONE** | — |
| 13 | P3 GreedyCausalPruner + RandomCircuitSampler | P3 | **DONE** | — |
| 14 | P3 `python -m experiments.phase1.single_agent_circuit_smoke` | P3 | **DONE** | — |
| 15 | P4 CrossAgentGraph (sender/message/receiver/outcome) | P4 | **DONE** | — |
| 16 | P4 SyntheticCausalBenchmark (known path S1→M1→R2→Y) | P4 | **DONE** | — |
| 17 | P4 CrossAgentGreedyPruner + message bridge intervention | P4 | **DONE** | — |
| 18 | P4 `python -m experiments.phase1.cross_agent_smoke` | P4 | **DONE** | — |
| 19 | RemediationCandidateExtractor + DeterministicSelector | P4 | **DONE** | — |
| 20 | Git member branches (m1…m4) | All | **DONE** | — |
| 21 | Full end-to-end integration smoke | All | **IN PROGRESS** | — |
| 22 | P1+P3 pairwise integration (target → activations) | P1+P3 | **IN PROGRESS** | model not frozen |
| 23 | P2+P4 pairwise integration (attack corpus → graph) | P2+P4 | **IN PROGRESS** | depends on #22 |

---

## End-of-Day Checkpoint (8 Oct evening)

### P1 (Target & Protocol)
- Command ran: `python -m target.runner --config configs/experiments/review_target.yaml`
- Tests passed: 15/15 unit + 3/3 integration
- Result file: `results/raw/p1_review_target_results.csv`
- Quantitative output: clean_pass=100%, attack_success=100% (5 fixture cases)
- Limitation: using fixture variations, not diverse synthetic cases yet
- What others can consume: `RunTrace` JSON files in `results/raw/`, `MockMCPClient`, `CaseLoader('synthetic')`

### P2 (Attack Corpus)
- Command ran: `python -m attacks.runner --config configs/experiments/review_attack.yaml`
- Tests passed: 16/16 unit
- Result file: `results/raw/p2_review_asr_table.csv`, `results/figures/p2_asr_plot.png`
- Quantitative output: 3 family ASR table with 95% bootstrap CI
- Limitation: mock target (attack always succeeds) — real target needed for meaningful ASR
- What others can consume: `AttackStore`, `CorpusBuilder`, `AttackEvaluator`, `bootstrap_ci`

### P3 (Mechanistic Discovery)
- Command ran: `python -m experiments.phase1.single_agent_circuit_smoke`
- Tests passed: 14/14 unit
- Result files: `results/raw/p3_smoke_component_ranking.csv`, `results/figures/p3_faithfulness_curve.png`
- Quantitative output: L1.H2 + L2.H1 recovered (top-2 causal), faithfulness=0.925 (99th percentile vs random)
- Limitation: toy model only — real open model not yet loaded
- What others can consume: `HookRegistry`, `ZeroAblation`, `GreedyCausalPruner`, `compute_faithfulness`

### P4 (Cross-Agent Graph)
- Command ran: `python -m experiments.phase1.cross_agent_smoke`
- Tests passed: 16/16 unit
- Result files: `results/raw/p4_smoke_intervention_results.csv`, `results/figures/p4_graph.png`
- Quantitative output: precision=1.0, F1=0.75, bridge_acc=1.0; message patch delta=-1.0 (causal)
- Limitation: synthetic known-path only — real traces not yet integrated
- What others can consume: `CrossAgentGraph`, `CrossAgentGreedyPruner`, `SyntheticCausalBenchmark`, `AttackEvaluator`

---

## Next Steps (9 October priority order)

1. **[P3] Load real small open model** (Qwen2.5-0.5B-Instruct or equivalent) — verify hook non-interference on real transformer
2. **[P1+P3] Real activation capture** — run target pipeline and capture `ActivationTrace` from sender/receiver
3. **[P4] Load real traces** — build `CrossAgentGraph` from P3-generated `ActivationTrace` fixtures
4. **[P2+P1] Real ASR** — run P2 attack corpus through P1 target harness (not mock)
5. **[P1] Diverse cases** — use `CaseLoader('synthetic')` with varied case mix in runner
6. **[All] End-to-end integration** — `experiments/phase1/end_to_end_smoke.py` full chain

---

## Known Bugs and Limitations

- P1: Runner uses fixture case variations rather than diverse synthetic cases (fix in 9 Oct session)
- P3: Toy model only — all smoke results are fixture-only (clearly marked)
- P2: Mock target — ASR is trivially 100% from mock (not a real model result)
- message_id and tool_call_ids use uuid4() — non-deterministic (by design — test updated accordingly)
- PTB-XL not downloaded — placeholder raises NotImplementedError
- Real model transformers dependency not yet installed

## Current bounded task — external WSO2 FHIR MCP review integration (2026-10-20)

Replace the custom MCP primary path with digest-pinned WSO2 FHIR MCP over Streamable HTTP and local HAPI FHIR R4. Preserve mock/replay only as explicit modes. Deterministic agents remain the reliable primary path; Qwen execution is a mandatory but qualification-gated Phase 1 deliverable. Implementation and partial live acceptance are complete. Host MCP SDK acquisition and full live 12-case qualification are blocked by the package proxy.
