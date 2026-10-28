# PROJECT_STATE.md
## Current Phase-1 implementation checkpoint: 2026-10-22

As of 2026-10-28, all features previously labelled optional in Phase 1 are
mandatory dependency-ordered deliverables. The first RL milestone now includes
a typed heterogeneous pruning environment and masked PPO implementation; its
model-free acceptance is in progress. RL is a prior-art baseline, not the
project novelty. Qualification and held-out split gates remain unchanged.

Advanced path/residual/head/SAE intervention mechanics and the fourth implicit-
preference attack-family generator are now implemented with synthetic/unit
acceptance. Real-model and benchmark evaluation remain unexecuted.

The mandatory Agent C policy/review path is also implemented additively with a
manifest-backed deterministic acceptance; the two-agent baseline is preserved.

Development continues on branch `lm`. Budgeted greedy/beam search, matched
random controls, receiver-only scope, strict Pareto repair selection, a
leakage-resistant correlational linear-probe baseline, portable checks, and
synthetic manifest-backed acceptance are implemented. The local
model-independent suite passes. Qwen2.5-1.5B remains blocked before access by
the frozen MQ-HW1 memory gate; its exact revision is also not yet frozen. See
`docs/PROJECT_STATE.md` for evidence and boundaries.

## Current reliability checkpoint: 2026-10-21

The sprint snapshot below is historical, not a claim that all current modes work.
See `docs/RELIABILITY_CHECKPOINT.md` and `docs/PROJECT_STATE.md`. The explicit mock
review demo passes all 48 HTTP actions. External WSO2 host transport is still
blocked by malformed HTTP framing; Qwen-over-FHIR is not qualified.

**Last updated:** 2026-10-08 23:30 IST  
**Sprint:** 4–8 October 2026 | **Review:** 8 October 2026  
**Status: SPRINT COMPLETE — ALL REVIEW EVIDENCE READY**

---

## Repository snapshot

| Item | State |
|------|-------|
| Git branch | `main` (all sprint work committed) |
| Member branches | `m1/target-harness`, `m2/attack-corpus`, `m3/mech-interventions`, `m4/cross-agent-graph` |
| Tests | **83/83 PASS** (77 unit+integration, 6 regression) |
| E2E smoke | **9/9 checks PASS** in 0.83 s |

---

## Demo commands (all verified via regression tests)

```bash
# P1 — Two-agent target harness
python -m target.runner --config configs/experiments/review_target.yaml

# P2 — Attack corpus + ASR evaluation
python -m attacks.runner --config configs/experiments/review_attack.yaml

# P3 — Single-agent mechanistic circuit
python -m experiments.phase1.single_agent_circuit_smoke

# P4 — Cross-agent graph + interventions
python -m experiments.phase1.cross_agent_smoke

# E2E — All four modules chained
python -m experiments.phase1.end_to_end_smoke

# Full test suite
python -m pytest tests/unit/ tests/integration/ -q
python -m pytest tests/regression/ -v
```

---

## Per-member status

### P1 — Target & Protocol Lead
- **Branch:** `m1/target-harness`
- **Status:** COMPLETE
- `target/agents/agent_a.py` — Intake agent (MockMCP + rule-based)
- `target/agents/agent_b.py` — Escalation agent (poison-override detection)
- `target/mcp/mock_client.py` — tool_description_poison, tool_output_inject
- `target/case_loader.py` — synthetic / fixture / PTB-XL stub
- `target/runner.py` — CLI with table + CSV output
- **Key results:** `results/raw/p1_review_target_results.csv`
- **Quantitative:** clean_pass=80% (4/8 diverse synthetic), attack_success=100%
- **Limitation:** rule-based agents only; real LLM integration deferred to 9 Oct

### P2 — Attack, Benchmark & Statistics Lead
- **Branch:** `m2/attack-corpus`
- **Status:** COMPLETE
- `attacks/corpus/builder.py` — 3 families × 5 = 15 deterministic attacks
- `attacks/adapters/mcptox_adapter.py` — MCPTox prior-art attribution (**not** a novelty claim)
- `attacks/evaluator.py` — ASR, conditional ASR, bootstrap CI
- `attacks/stats.py` — `bootstrap_ci`, `paired_mcnemar`, `effect_size_odds_ratio`
- **Key results:** `results/raw/p2_review_asr_table.csv`, `results/figures/p2_asr_plot.png`
- **Quantitative:** ASR=100% (mock target), 95% CI computed per family
- **Limitation:** mock target — ASR against real model is unmeasured until P1+P2 integration

### P3 — Mechanistic Discovery & RL Lead
- **Branch:** `m3/mech-interventions`
- **Status:** COMPLETE
- `instrumentation/hooks/hook_registry.py` — non-interference verified
- `causal/interventions/operators.py` — ZeroAblation, MeanAblation, ActivationPatch
- `causal/metrics/faithfulness.py` — F(C), necessity, benign_damage
- `discovery/greedy/pruner.py` — GreedyCausalPruner
- **Key results:** `results/raw/p3_smoke_component_ranking.csv`, `results/figures/p3_faithfulness_curve.png`
- **Quantitative:** L1.H2+L2.H1 recovered (top-2), faithfulness=0.925, 99th percentile vs random
- **Limitation:** ToyTransformer only — real model hook integration deferred to 9 Oct

### P4 — Cross-Agent Causality & Remediation Lead
- **Branch:** `m4/cross-agent-graph`
- **Status:** COMPLETE
- `causal/candidate_graph/cross_agent_graph.py` — heterogeneous sender/message/receiver/outcome
- `causal/bridge/intervention.py` — message patch, sender/receiver ablation
- `causal/validation/synthetic_benchmark.py` — known path S1→M1→R2→Y
- `discovery/greedy/cross_agent_pruner.py` — CrossAgentGreedyPruner
- `remediation/selector/deterministic_selector.py` — Pareto-efficient selection
- **Key results:** `results/raw/p4_smoke_intervention_results.csv`, `results/figures/p4_graph.png`
- **Quantitative:** precision=1.0, F1=0.75, bridge_acc=1.0, message patch delta=-1.0

---

## Machine-generated result files

| File | Who | What |
|------|-----|------|
| `results/raw/p1_review_target_results.csv` | P1 | Run table: 8 cases × 2 modes |
| `results/raw/p2_review_attack_results.csv` | P2 | 15 per-attack predictions |
| `results/raw/p2_review_asr_table.csv` | P2 | ASR + 95% CI per family |
| `results/raw/p3_smoke_component_ranking.csv` | P3 | 12 components ranked by effect |
| `results/raw/p3_smoke_intervention_results.csv` | P3 | Greedy pruning steps |
| `results/raw/p3_smoke_circuit_result.json` | P3 | CircuitResult schema |
| `results/raw/p4_smoke_intervention_results.csv` | P4 | Sender/message/receiver deltas |
| `results/raw/p4_smoke_circuit_result.json` | P4 | CircuitResult + evaluation |
| `results/raw/e2e_smoke_run_summary.csv` | All | E2E run table |
| `results/raw/e2e_smoke_summary.json` | All | E2E JSON summary |
| `results/figures/p2_asr_plot.png` | P2 | Bar chart with 95% CI |
| `results/figures/p3_faithfulness_curve.png` | P3 | Faithfulness vs size + baseline |
| `results/figures/p4_graph.png` | P4 | Cross-agent graph viz |
| `results/figures/e2e_smoke_combined.png` | All | Combined P3+P4 metrics plot |

---

## Known limitations (explicitly stated, not hidden)

1. **No real LLM**: all agents are rule-based — real model integration is the 9 Oct priority
2. **PTB-XL**: not downloaded; `CaseLoader('ptbxl')` raises `NotImplementedError` by design
3. **Mock target ASR**: P2 ASR is trivially 100% from mock; meaningful ASR requires real P1 runs
4. **ToyTransformer**: P3 causal results are on synthetic toy model — Tracr calibration deferred
5. **uuid4 non-determinism**: message_id and tool_call_ids are random per-run (documented in tests)
6. **pandas**: not in base deps (`pyproject.toml`) but imported by `causal/bridge/intervention.py`

---

## Next steps (9 October)

**Priority 1 — Real model integration (P3)**
- Choose: Qwen2.5-0.5B-Instruct (recommended) or GPT-2 (lighter fallback)
- Command: `pip install transformers accelerate`
- Test hook non-interference on real model before any other real-model work
- Record HuggingFace repo + git revision hash in `configs/models/model_registry.yaml`

**Priority 2 — P1+P3 pairwise (activate real traces)**
- Run target pipeline on ESCALATE cases → capture `ActivationTrace` from sender
- Save to `results/raw/activation_cache/`
- Verify P4 `CrossAgentGraph.load_from_activation_traces()` can consume them

**Priority 3 — P2+P1 real ASR**
- Run P2 attack corpus through actual P1 target (not mock)
- Report `conditional_asr` (success rate on cases where clean run was correct)

**Priority 4 — Add pandas to pyproject.toml**
- `causal/bridge/intervention.py` imports pandas — add `pandas>=2.0` to deps

**Priority 5 — Tracr calibration (P3, mandatory before Phase 1 paper claims)**
- Implement `tests/integration/test_tracr_calibration.py`
- Target: faithfulness on Tracr-compiled circuits ≥ 0.9

---

## Binding rules (from RESEARCH_CONTRACT.md)

- Schema version: **v0.1.0** — frozen until team vote
- No silent schema changes — use additive adapters
- All results traced to raw files + commands (no manual copy-paste)
- MCPTox is prior art — results labelled AETHER-CATF
- Feature freeze: **8 November 2026**
- No new novelty claims after **29 October 2026**
