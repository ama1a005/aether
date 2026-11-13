# AGENT_C_RUNBOOK.md — SUPPORT-02

**Owner:** Friend B | **Branch:** `amala` | **Deadline:** 19 November 2026

---

## Purpose

Demonstrate that the three-agent pipeline (A -> B -> C) executes on **real Qwen 1.5B**,
with Agent C review isolated from the causal core. Record controlled A/B baseline and
new measurements. Evidence class must be `real_model_cpu_float32`.

---

## Prerequisites

Same as SUPPORT-01 (Qwen 1.5B weights, Python 3.11, 8 GB RAM).

---

## Step 1 — Dry Run

```powershell
python -m experiments.supporting_nov19.agent_c.runner `
    --config configs/supporting_nov19/agent_c_qwen15b.json `
    --dry-run
```

Expected: `Dry-run PASSED: Agent C config validated.`

---

## Step 2 — Execute

```powershell
python -m experiments.supporting_nov19.agent_c.runner `
    --config configs/supporting_nov19/agent_c_qwen15b.json `
    --execute `
    --output-root results/phase1/agent_c/qwen15b
```

Records written to `results/phase1/agent_c/qwen15b/<run_id>/records/`.

---

## Acceptance Criteria (gate: `real_qwen_agent_c`)

- Agent C review outcomes recorded with real Qwen B decisions as inputs
- Both clean and attacked cases included
- Agent B raw decision preserved separately from Agent C reviewed decision
- `results/phase1/agent_c/qwen15b/<run_id>/summary.json` written from real evidence
- `overall: PASS` set only after independent verification of real outputs

---

## Isolation Rules

- Agent C does NOT alter Agent B logged `agent_b_decision` in `ThreeAgentResult`
- Agent C is NOT part of the causal core (DCMG/BVP); results are independent supporting evidence
- Do NOT use validation or test splits
