# AETHER Research Contract

**Version:** 0.1.0  
**Date:** 2026-10-04  
**Status:** FROZEN — no individual may silently amend this document.

---

## One-Sentence Project Identity

> We introduce a cross-agent causal circuit-discovery framework that traces adversarial trust failures from a sender model's internal computation, through an A2A message, into a receiver model's internal computation, and uses the resulting minimal causal mechanism to guide targeted remediation.

---

## What AETHER Is

AETHER is a mechanistic audit layer for multi-agent AI systems that turns a successful attack trace into a causal explanation and a targeted repair candidate.

---

## Core Novelty Hierarchy

### N1 — Cross-Agent Causal Circuit Discovery (REQUIRED — Phase 1 headline)

A causal circuit-discovery procedure whose candidate graph spans:
- internal components of Sender Agent A
- one or more structured/textual components of an A2A message
- internal components of Receiver Agent B
- the final unsafe trust decision

**What is new:** the cross-boundary mechanistic causal formalism and discovery procedure — NOT RL, NOT tool poisoning, NOT multi-agent systems in general.

### N2 — Heterogeneous Cross-Boundary Search/Formalism (required if N1 uses RL/search)

Intervention operators and search representation reasoning over model-internal nodes, message nodes, and bridge edges.

### N3 — Mechanism-Guided Intervention Selection (Phase 1 minimum demonstration)

Choosing intervention point based on discovered causal mechanism, not fixed defense location.

---

## What Is NOT Novel

The following are infrastructure, benchmarks, or evaluation contexts — not AETHER contributions:

- MCP tool poisoning (MCPTox is prior art)
- RL-based circuit discovery in general (MechRL is prior art)
- Multi-agent activation probing (NARCBench is prior art)
- Cross-agent causal influence at message level (CASPIAN is prior art)
- Use of MCP, A2A, RL, activation steering, medical/IoMT setting, RAG, dashboards, or LLM code generation

---

## Key Definitions

### Attack Success

For targeted attacks: `ASR = successful_targeted_attacks / eligible_attack_attempts`

Eligibility determined BEFORE inspecting model output. No silent drops.

### Circuit Faithfulness

```
F(C) = 1 - |Δ_full - Δ_C| / (|Δ_full| + ε)
```

where `Δ = T(x_adv) - T(x_clean)` and `T(x) = logit_unsafe(x) - logit_safe(x)`.

### Circuit Minimality

Operational definition: no node can be removed without faithfulness falling below threshold. NOT claimed as global minimality.

### Causal Evidence (vs Correlational)

- Correlational: activation probe predicts outcome
- **Causal (required):** intervening on the component changes the outcome

---

## Binding Rules

1. Cross-agent causal circuit discovery is the scientific core.
2. MCPTox-style tool poisoning is an attack source, not the novelty.
3. MechRL/RL is a method/baseline, not the novelty.
4. The medical/IoMT setting is an evaluation harness only.
5. PTB-XL supplies standardized case provenance.
6. BFCL establishes benign tool competence.
7. Tracr + IOI/Greater-Than calibrate the circuit code.
8. The final test set is locked — no tuning on it.
9. No LLM judge controls a primary endpoint when deterministic labels exist.
10. No result accepted without: run config, dataset hash, model revision, seed, raw outputs.
11. No new novelty added after 29 October unless it fixes a methodological flaw.
12. Feature freeze: 8 November.

---

## Intervention Validity

Every intervention experiment MUST record:
- exact model checkpoint
- exact tokenizer
- layer/head/node ID
- token positions
- clean/attacked source
- seed
- prompt
- generation parameters
- output
- metric delta

No unlogged manual intervention counts as paper evidence.
