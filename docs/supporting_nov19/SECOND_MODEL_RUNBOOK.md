# SECOND_MODEL_RUNBOOK.md — SUPPORT-04

**Owner:** Friend B | **Branch:** `amala` | **Deadline:** 19 November 2026

---

## Purpose

Qualify a **different** open-weight model on all AETHER behavioral and instrumentation
gates. This is NOT a rename of the existing Qwen 1.5B checkpoint, and NOT the
Qwen 0.5B model (which failed balanced qualification).

---

## Proposed Second Model

`microsoft/Phi-3-mini-4k-instruct` — subject to revision pinning before execution.

**Before executing:** Download the model, record its exact HuggingFace revision SHA,
and update `configs/supporting_nov19/second_model_manifest.json` with the real revision.

---

## Prerequisites

1. Python 3.11 venv with project deps
2. Second model weights downloaded and cached
3. Exact model revision recorded in config
4. At least 4–8 GB RAM free

---

## Step 1 — Pin the Model Revision

```powershell
# After downloading the model, record its revision:
python -c "
from transformers import AutoModelForCausalLM
m = AutoModelForCausalLM.from_pretrained('microsoft/Phi-3-mini-4k-instruct')
print(m.config._commit_hash)
"
# Update configs/supporting_nov19/second_model_manifest.json with this value
```

---

## Step 2 — Dry Run

```powershell
python -m experiments.supporting_nov19.second_model.runner `
    --config configs/supporting_nov19/second_model_manifest.json `
    --dry-run
```

Expected: `Dry-run PASSED: Second model manifest validated.`

If `model_revision` is `"unknown"`, dry-run will FAIL — update the config first.

---

## Step 3 — Execute

```powershell
python -m experiments.supporting_nov19.second_model.runner `
    --config configs/supporting_nov19/second_model_manifest.json `
    --execute `
    --output-root results/phase1/model_qualification/second_model
```

---

## Full Qualification Gates Required

The gate `second_model_qualification` requires ALL of the following (not just a load test):

1. 24/24 clean and eligible attacked cases passing
2. Message-level rescue and induction 12/12 in each direction
3. Instrumentation and capture gates (activation hooks working)
4. `results/phase1/model_qualification/second_model/summary.json` with `overall: PASS`
   set ONLY from verified execution of all gates

---

## What Does NOT Qualify

- Loading the 0.5B model (failed balanced qualification)
- Renaming the existing Qwen 1.5B checkpoint
- A partial load test without behavioral gates
- Inherited evidence from the 1.5B qualification
