# PROJECT STATE

Date: 2026-10-08  
Stable contracts version: 0.1.0  
Selected model: TBD (Qwen2.5-0.5B-Instruct or Qwen2.5-1.5B-Instruct preferred for hardware fit)  
Primary development dataset: PTB-XL development folds / fixtures  
Primary attack anchor: MCPTox  

---

## P1 Target
Status: SCAFFOLDED — contracts and fixtures in place, real model integration pending  
Working command: `python -m target.runner --config configs/experiments/review_target.yaml`  
Passing tests: Schema fixture parse tests  
Blocking issues: Model not yet selected/loaded  
Artifacts: `tests/fixtures/clean_run_trace.json`, `tests/fixtures/attacked_run_trace.json`

## P2 Attacks/Benchmark
Status: SCAFFOLDED — attack schema, corpus fixtures, evaluator stub in place  
Working command: `python -m attacks.runner --config configs/experiments/review_attack.yaml`  
Passing tests: AttackSpec schema tests  
Blocking issues: Full MCPTox integration pending  
Artifacts: `tests/fixtures/clean_attack_spec.json`, `tests/fixtures/poison_attack_spec.json`

## P3 Mechanistic Instrumentation
Status: IN PROGRESS — hook registry, ablations, greedy pruning, faithfulness curve  
Working command: `python -m experiments.phase1.single_agent_circuit_smoke`  
Passing tests: hook non-interference, zero ablation locality, cache roundtrip  
Blocking issues: Model selection pending; running on synthetic toy model for now  
Artifacts: `results/raw/p3_smoke_intervention_results.csv`, `results/figures/p3_faithfulness_curve.png`

## P4 Cross-Agent Causality
Status: IN PROGRESS — graph schema, node types, interventions, greedy cross-agent search  
Working command: `python -m experiments.phase1.cross_agent_smoke`  
Passing tests: graph serialization, all node types, synthetic known-path test  
Blocking issues: Real activation traces depend on P3 model freeze  
Artifacts: `results/raw/p4_smoke_intervention_results.csv`, `results/figures/p4_graph.png`

---

## Shared Decisions

- Python 3.11, pytest, numpy, torch (no transformers dependency enforced yet)
- Experiment ID pattern: `P0_<module>_<yyyymmdd>_<shortname>_<seed>`
- Fixtures in `tests/fixtures/` are ground truth for schema compliance
- Contracts frozen at v0.1.0 — no silent changes
- Review checkpoint: 8 October 2026

## Known Research Limitations

- Model not yet selected/frozen — all smoke runs use a tiny synthetic toy transformer
- PTB-XL not yet downloaded — fixture cases used for review
- MCPTox official evaluator not yet integrated
- RL environment not yet implemented (greedy baselines prioritized)
- Single model family only in Phase 1

## Failed Experiments

None yet — first smoke runs in progress

## Next-Day Highest-Value Tasks (9 October)

1. P3: Select and load real small open model, verify hook non-interference
2. P4: Load real activation traces from P3 into cross-agent graph
3. P1+P2: Pairwise integration — attack → target pipeline
4. P3+P4: Pairwise integration — interventions → cross-agent graph
