# RED_TEAM_RUNBOOK.md — SUPPORT-01

**Owner:** Friend B | **Branch:** `amala` | **Deadline:** 19 November 2026

---

## Purpose

Demonstrate that the red-team orchestration operates against **real pinned Qwen 1.5B**
model decisions, not a rule-based simulator. Evidence class must be `real_model_cpu_float32`.

---

## Prerequisites

1. Python 3.11 venv activated with project dependencies installed
2. Qwen/Qwen2.5-1.5B-Instruct revision `989aa7980e4cf806f80c7fef2b1adb7bc71aa306` cached locally
3. At least 8 GB RAM free; at least 4 GB disk for weights
4. Working directory: repo root on branch `amala`

```powershell
py -3.11 -m venv .venv-support
.\.venv-support\Scripts\Activate.ps1
python -m pip install -e .
git rev-parse HEAD
```

---

## Step 1 — Dry Run (no model loading)

```powershell
python -m experiments.supporting_nov19.red_team.runner `
    --config configs/supporting_nov19/red_team_qwen15b.json `
    --dry-run
```

Expected output: `Dry-run PASSED: config and prerequisites validated.`

---

## Step 2 — Execute (loads real Qwen)

```powershell
python -m experiments.supporting_nov19.red_team.runner `
    --config configs/supporting_nov19/red_team_qwen15b.json `
    --execute `
    --output-root results/phase1/red_team/qwen15b
```

Attempt records written to `results/phase1/red_team/qwen15b/<run_id>/attempts/*.json`.

---

## Step 3 — Independent Verification

```powershell
python -m experiments.supporting_nov19.red_team.verifier `
    --run-dir results/phase1/red_team/qwen15b/<run_id> `
    --output results/phase1/red_team/qwen15b/<run_id>/verification.json
```

Acceptance: `overall: PASS` only if `evidence_class == "real_model_cpu_float32"`,
no `"started"` attempts remain, and real model outputs are present.

---

## Acceptance Criteria (gate: `real_qwen_red_team`)

- Real Qwen model outputs in raw attempt records (not fixtures)
- Clean/attacked pairs preserved for all families
- No postselection by attack outcome
- `results/phase1/red_team/qwen15b/<run_id>/summary.json` from verified evidence only
- Source commit, model revision, seed, run_id logged

---

## What NOT to do

- Do NOT copy outcomes from rule-based smoke tests into real-model summary
- Do NOT set `overall: PASS` without genuine execution and independent verification
- Do NOT use validation or test splits
- Do NOT modify `attacks/orchestration.py` or any frozen core file
