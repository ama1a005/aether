# Qwen SAE training freeze v1 — human review package

## Decision requested

Review the prospective protocol at
`configs/experiments/qwen_sae_training_freeze_v1.json`.

SHA-256:
`5dd220297a159a712e114489ca8872ab0a7badf258e410e0ddffa65883ce1272`

This proposal does not authorize model access, training, validation/test access,
or a causal SAE-feature claim. It freezes a development-only reconstruction and
sparsity experiment before execution.

## What is frozen

- Qwen2.5-1.5B-Instruct and its immutable qualified revision.
- Receiver layer-22 attention output, width 1536.
- Full non-padding prompt-token activations from the declared external archive.
- Sixteen discovery cases for training and four development-audit cases for
  checkpoint selection/evaluation; the four acceptance cases remain excluded.
- Train-only standardization, a 1536-to-3072 ReLU linear SAE, Adam optimization,
  three seeds, complete loss, early stopping and deterministic tie-breaking.
- Reconstruction, sparsity and dead-feature acceptance metrics.
- Minimum 10,000 training rows, exact archive hashing, required artifacts and
  zero validation/test executions.

## Why execution is currently blocked

The locally retained final-token capture produces only 32 train rows and 8
audit rows. It fails the protocol's minimum-row gate and must not be used as a
scientific substitute. The full-token archive with the frozen SHA-256 must be
located or regenerated under a separately reviewed capture protocol.

## Reviewer checklist

- [ ] Model, revision, component and width are correct.
- [ ] Train, audit and excluded case partitions are disjoint and acceptable.
- [ ] All-non-padding-token sampling is scientifically appropriate.
- [ ] Minimum training-row count is adequate.
- [ ] Architecture, optimization, seeds and selection rule are acceptable.
- [ ] Reconstruction, sparsity and dead-feature thresholds are acceptable.
- [ ] Claim boundary excludes causal feature claims.
- [ ] Validation and test access remain zero.
- [ ] The exact SHA-256 above was independently recomputed.

If approved, record an explicit statement naming this version and exact hash.
Do not edit the proposal after approval; any correction requires a new version
and hash.
