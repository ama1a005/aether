# BLOCKED_MISSING_CAPTURE_DATA.md

**Branch:** `amala`  
**Author:** Friend B — supporting-experiments lead  
**Date:** 2026-11-13  
**Blocking:** SUPPORT-03 (Trained SAE Evaluation) — `--execute` mode

---

## Blocked Item

The SAE training and evaluation pipeline (`experiments/supporting_nov19/sae/`)
requires the externally-sourced tensor archive of captured Qwen 1.5B activations.

## External Tensor Archive Details

| Item | Value |
|---|---|
| Reported SHA256 | `7890212a8e7a4eb099be86bc572cd6172fd1c45b839f695e56e6ba4a46e97b21` |
| Reported size | 4.87 GB |
| Available locally | **NO** |
| In git | No (correctly excluded — binary too large) |
| Expected format | `.npy` files per component ID |
| Expected components | `sender.module.L22.attention_output`, `receiver.module.L22.attention_output`, `receiver.head.L20.H5.pre_o_proj`, `receiver.head.L22.H7.pre_o_proj` |

## What Is Blocked

1. **SAE training** (`experiments/supporting_nov19/sae/trainer.py`) — cannot train
   without real activation data
2. **SAE evaluation** (`experiments/supporting_nov19/sae/runner.py --execute`) —
   requires a trained checkpoint, which requires the archive
3. **Feature ablation / patching** — no activations to intervene on

## What Is NOT Blocked

1. **Code implementation** — fully complete and tested
2. **Dry-run validation** — `--dry-run` works and validates config
3. **Unit tests** — all SAE-related unit tests pass (using synthetic test data)
4. **Data loader** (`experiments/supporting_nov19/sae/data_loader.py`) — implemented
   and ready to use once data is available

## Required Action

1. Obtain the tensor archive from an authorized external source (e.g., Kaggle
   notebook output, shared cloud storage)
2. Verify SHA256: `7890212a8e7a4eb099be86bc572cd6172fd1c45b839f695e56e6ba4a46e97b21`
3. Extract to a local directory (e.g., `data/activations/`)
4. Run: `python -m experiments.supporting_nov19.sae.trainer --data-dir data/activations --component-id sender.module.L22.attention_output --output-dir results/phase1/sae/qwen15b/trained_checkpoint`
5. Then run: `python -m experiments.supporting_nov19.sae.runner --execute --checkpoint-dir results/phase1/sae/qwen15b/trained_checkpoint`

## Timeline Impact

This does NOT block the 19 November deadline for code delivery. The code scaffold,
tests, and dry-run validation are complete. Actual SAE evidence generation can
proceed once the tensor archive is obtained.
