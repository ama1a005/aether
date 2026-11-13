# SAE_RUNBOOK.md — SUPPORT-03

**Owner:** Friend B | **Branch:** `amala` | **Deadline:** 19 November 2026

---

## Purpose

Test a **trained** sparse autoencoder (SAE) matched to actual Qwen component
representations, verify reconstruction acceptance, and perform causal probing.
A randomly-initialized SAE does NOT satisfy this gate.

---

## Prerequisites

1. Python 3.11 venv with project deps (`pip install -e .`)
2. Qwen 1.5B weights (revision `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`)
3. External 4.87 GB development-capture tensor archive:
   - SHA256: `7890212a8e7a4eb099be86bc572cd6172fd1c45b839f695e56e6ba4a46e97b21`
   - **NOT available locally** — must be sourced from authorized external location
   - Verify SHA before use: `Get-FileHash archive.pt -Algorithm SHA256`
4. Trained SAE checkpoint directory (produced externally from the tensor archive)
   containing `metadata.json` and `weights.npz`

---

## Step 1 — Dry Run

```powershell
python -m experiments.supporting_nov19.sae.runner `
    --config configs/supporting_nov19/sae_qwen15b.json `
    --checkpoint-dir <path/to/sae/checkpoint> `
    --dry-run
```

Expected: `Dry-run PASSED: SAE config validated.`

---

## Step 2 — Execute

```powershell
python -m experiments.supporting_nov19.sae.runner `
    --config configs/supporting_nov19/sae_qwen15b.json `
    --checkpoint-dir <path/to/sae/checkpoint> `
    --execute `
    --output-root results/phase1/sae/qwen15b
```

---

## Acceptance Criteria (gate: `trained_sae_qwen_evaluation`)

- SAE checkpoint trained on actual Qwen 1.5B activations (not random init)
- Reconstruction error below `max_relative_reconstruction_error` threshold
- Component ID matches a QCI-2 candidate component
- Real Qwen activations captured (not synthetic tensors)
- `results/phase1/sae/qwen15b/<run_id>/summary.json` from verified real evidence

---

## Critical Blockers

The tensor archive (4.87 GB) is not in the repository and cannot be assumed present.
Do NOT claim SAE training used these tensors without an authorized copy and matching SHA.
Do NOT proceed to `overall: PASS` without genuine reconstruction validation on real activations.
