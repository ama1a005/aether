# Qwen SAE training freeze v1.1 — data-source amendment review

## Decision requested

Review the prospective correction at
`configs/experiments/qwen_sae_training_freeze_v1_1_amendment.json`.

SHA-256:
`30c7b828c1b237ff8d8d5855bd78bb285c73a0986e5f61555004e9c6485a4ff6`

V1 remains approved and immutable. This amendment changes only the source of
the SAE training and checkpoint-selection activations. It does not authorize
execution until this exact amendment is separately approved.

## Why v1 cannot execute as written

The 16 frozen receiver training cases contain 3,872 non-padding prompt tokens.
V1 requires at least 10,000 unique training rows. The old full-token archive
would preserve more components but cannot create additional receiver layer-22
tokens. Duplicating rows or silently lowering the minimum would violate the
approved protocol.

## Proposed correction

- Train on exactly 57,344 tokens from the pinned WikiText-2 raw training split.
- Reserve the next 8,192 tokens from the same pinned corpus solely for
  checkpoint selection.
- Use repository order, deterministic empty-row removal, the pinned Qwen
  tokenizer, and one EOS separator between documents.
- Capture 256 full token positions per block at Qwen layer-22 attention output.
- Keep all AETHER cases out of SAE training and checkpoint selection.
- After selecting the SAE, evaluate it once on the unchanged four-case AETHER
  development-audit cohort in clean and attacked conditions.
- Retain v1 architecture, optimizer, loss, seeds, thresholds, artifacts,
  validation/test locks, and reconstruction-only claim boundary.

The corpus is `Salesforce/wikitext`, configuration `wikitext-2-raw-v1`, pinned
at revision `de54f133ef530c2e9b46c532f95a01c446ff0f1d`. The runner must retain the
downloaded file hashes and exact selected token-ID hash.

## Reviewer checklist

- [ ] The arithmetic blocker is correctly stated.
- [ ] An independent language corpus is appropriate for unsupervised SAE training.
- [ ] Dataset identity, revision, configuration and deterministic selection are sufficient.
- [ ] The 57,344/8,192 partition is fixed before observing SAE results.
- [ ] AETHER audit cases cannot influence training or checkpoint selection.
- [ ] CUDA float32 without quantization/offload is acceptable for this supporting study.
- [ ] V1 thresholds, architecture, seeds and claim boundary remain unchanged.
- [ ] Validation and test access remain zero.
- [ ] The exact amendment SHA-256 above was independently recomputed.

Approval must name v1.1 and the exact hash. Any further correction requires a
new immutable amendment.
