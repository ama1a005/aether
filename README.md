# AETHER

## Intermediate review demo

The removable localhost review application is documented in [`DEMO_README.md`](DEMO_README.md). It uses twelve explicitly synthetic cases and imports existing AETHER core primitives; research modules do not depend on the demo. Start it from PowerShell with `powershell -ExecutionPolicy Bypass -File scripts/run_review_demo.ps1` after installing the pinned frontend dependencies.
**Cross-Agent Causal Circuit Discovery and Mechanism-Guided Remediation for Adversarial Trust Failures in MCP/A2A Multi-Agent Systems**

Sprint 4–8 Oct 2026 | Phase 1 deadline: 16 Nov 2026

---

## Quick start

```bash
git clone <repo>
cd aether
pip install torch numpy matplotlib pyyaml pytest

# All four demo commands
python -m target.runner --config configs/experiments/review_target.yaml
python -m attacks.runner --config configs/experiments/review_attack.yaml
python -m experiments.phase1.single_agent_circuit_smoke
python -m experiments.phase1.cross_agent_smoke

# Full end-to-end integration (chains all four modules)
python -m experiments.phase1.end_to_end_smoke

# Test suite
python -m pytest tests/unit/ tests/integration/ -q          # 77 tests, <10s
python -m pytest tests/regression/ -v                        # 6 regression, ~25s
```

---

## Repository structure

```
aether/
├── contracts/            # Frozen shared schemas v0.1.0
│   └── schemas.py        # PatientCase, A2AMessageRecord, AttackSpec, RunTrace,
│                         #   ActivationTrace, InterventionSpec, CircuitResult
│
├── target/               # P1 — Two-agent target harness
│   ├── agents/           #   AgentA (intake), AgentB (escalation decision)
│   ├── mcp/              #   MockMCPClient (tool_description_poison, tool_output_inject)
│   ├── a2a/              #   A2AMessageBuilder
│   ├── case_loader.py    #   CaseLoader (synthetic / fixture / ptbxl-stub)
│   ├── decision_parser.py
│   ├── trace_logger.py
│   └── runner.py         #   CLI entry-point
│
├── attacks/              # P2 — Attack corpus & evaluation
│   ├── corpus/           #   CorpusBuilder, AttackStore
│   ├── adapters/         #   MCPToxAdapter (prior-art attribution)
│   ├── templates/        #   6 frozen attack templates
│   ├── a2a/              #   A2AManipulator
│   ├── evaluator.py      #   AttackEvaluator (ASR, conditional ASR)
│   ├── stats.py          #   bootstrap_ci, paired_mcnemar, effect_size_odds_ratio
│   └── runner.py         #   CLI entry-point
│
├── instrumentation/      # P3 — Activation hooks
│   ├── hooks/            #   HookRegistry (non-interference verified)
│   ├── cache/            #   ActivationCache (tensor save/load)
│   └── trace_capture.py
│
├── causal/               # P3+P4 — Causal analysis
│   ├── interventions/    #   ZeroAblation, MeanAblation, ActivationPatch
│   ├── metrics/          #   faithfulness F(C), necessity, benign_damage
│   ├── candidate_graph/  #   CandidateGraphBuilder, CrossAgentGraph
│   ├── bridge/           #   MessageBridge, CrossAgentInterventionRunner
│   └── validation/       #   SyntheticCausalBenchmark, circuit metrics
│
├── discovery/            # P3+P4 — Circuit discovery
│   ├── greedy/           #   GreedyCausalPruner, CrossAgentGreedyPruner
│   └── random_baseline/  #   RandomCircuitSampler
│
├── remediation/          # P4 — Intervention selection
│   ├── candidates/       #   RemediationCandidateExtractor
│   └── selector/         #   DeterministicInterventionSelector (Pareto)
│
├── experiments/
│   └── phase1/
│       ├── single_agent_circuit_smoke.py   # P3 demo
│       ├── cross_agent_smoke.py            # P4 demo
│       └── end_to_end_smoke.py             # Full integration (P1→P2→P3→P4)
│
├── tests/
│   ├── unit/             # 77 unit + integration tests
│   ├── integration/
│   └── regression/       # 6 regression tests (subprocess, verifies all demos)
│
├── configs/
│   └── experiments/
│       ├── review_target.yaml   # P1 config (synthetic cases, seed=42)
│       └── review_attack.yaml   # P2 config (3 families, n_per_family=5)
│
├── benchmarks/REGISTRY.yaml     # MCPTox, BFCL, PTB-XL, Tracr, IOI, AETHER-CATF
├── data/attack_cases/           # 15 generated attack specs + MANIFEST.json
├── results/
│   ├── raw/                     # CSVs, JSONs, RunTraces
│   └── figures/                 # PNG plots (matplotlib, Agg backend)
│
├── RESEARCH_CONTRACT.md         # Novelty bounds, metric definitions, binding rules
├── AGENTS.md                    # Coding-agent operating rules
├── PROJECT_STATE.md             # Current sprint status
└── TASK.md                      # Daily task board
```

---

## Key quantitative results (8 October review)

| Member | Command | Key metric |
|--------|---------|------------|
| P1 | `python -m target.runner ...` | clean_pass=80%, attack_success=100% (tool_description_poison, rule-based) |
| P2 | `python -m attacks.runner ...` | ASR=100% (mock), 3 families, 95% bootstrap CI |
| P3 | `python -m experiments.phase1.single_agent_circuit_smoke` | faithfulness=0.925, 99th pct vs random, L1.H2+L2.H1 recovered |
| P4 | `python -m experiments.phase1.cross_agent_smoke` | precision=1.0, F1=0.75, bridge_acc=1.0, message patch delta=-1.0 |
| All | `python -m experiments.phase1.end_to_end_smoke` | 9/9 checks PASS in 0.83 s |

> **Scope note:** All P3/P4 results use a ToyTransformer and SyntheticCausalBenchmark respectively.
> Real model integration is scheduled for 9–15 October.
> P2 ASR uses a mock target — real ASR against the P1 pipeline is the next integration milestone.

---

## Branch map

| Branch | Owner | Contents |
|--------|-------|----------|
| `main` | All | Shared contracts, fixtures, configs, governance |
| `m1/target-harness` | Member 1 | `target/` |
| `m2/attack-corpus` | Member 2 | `attacks/` |
| `m3/mech-interventions` | Member 3 | `instrumentation/`, `causal/interventions/`, `discovery/greedy/pruner.py` |
| `m4/cross-agent-graph` | Member 4 | `causal/candidate_graph/cross_agent_graph.py`, `causal/bridge/`, `discovery/greedy/cross_agent_pruner.py`, `remediation/` |

---

## Important constraints

- **No real LLM calls**: everything runs on CPU with rule-based / toy models
- **No GPU required**: all tests pass on CPU in < 30 s total
- **MCPTox is prior art**: results labelled `AETHER-CATF`, never `MCPTox ASR`
- **PTB-XL not loaded**: raises `NotImplementedError` by design — restricted dataset
- **Schema v0.1.0 frozen**: no field changes without team vote
