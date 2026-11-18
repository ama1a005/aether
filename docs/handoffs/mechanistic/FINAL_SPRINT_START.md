# Member 3 final-sprint start audit

Date: 2026-11-18 (Asia/Kolkata)

Branch: `m3/mech-interventions`

Starting commit: `449d607ffec38cb43165d2e900ec4e5b4449c38c`

## Baseline verification

The bounded Member-3 baseline completed with **67 passed and 2 expected
skips**. The skips are real-model hook non-interference tests and are not local
execution evidence. No validation or test split was accessed.

## Available retained resources

- Qualified model identity: `Qwen/Qwen2.5-1.5B-Instruct` at immutable revision
  `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`.
- Retained development capture summary SHA-256:
  `2e34222a2f207acfad9c0a48e091fef0e8f189ee7698c80629d0615a7c0ae77d`.
- Retained activation-artifact registry SHA-256:
  `1eb91d4754b6dc5fbc951b089ce4fbd855b10fff757c56493f9dedbf63105909`.
- The retained capture contains 20 development cases, with 16 discovery cases
  and 4 untouched development-audit cases. Acceptance cases 000, 001, 012 and
  013 remain excluded.
- Exact receiver layer-22 attention tensors are available for clean and
  attacked conditions. Strict conversion produces 40 final-token vectors of
  width 1536 and dataset SHA-256
  `a4e3ed9c07a48716c32f7d316acd9cff274964dbd6488e4c357e1327b1a01cf6`.
- The retained `notebooks/Results` material is external/untracked. It must not
  be added to Git; only immutable identities and verified derived manifests may
  be committed.

## Resource state

- Python: repository `.venv`, Python 3.11.9.
- RAM observed during audit: 15.67 GiB total, 2.38 GiB available.
- Disk free: 107.35 GiB.
- GPU visible: NVIDIA GeForce RTX 2050, 4096 MiB, 3883 MiB free. The qualified
  primary-model condition remains CPU float32; GPU visibility does not change
  that frozen condition.

## Confirmed implementation defect and correction

The pre-existing supporting SAE trainer was not compatible with the canonical
`causal.interventions.sae.load_sae_checkpoint` interface. Its matrix
orientations were transposed relative to the loader, and its metadata contained
unrecognized fields while omitting required provenance and weight hashes. It
also allowed an unrelated `.npy` file to be silently substituted for a missing
component.

The Member-3 branch now writes the one canonical checkpoint format, separates
training diagnostics from strict metadata, records verified dataset and weight
hashes, and refuses component substitution. A new unit test trains a small SAE,
saves it, loads it with the production codec and encodes tensors successfully.

## Scientific blocker discovered

The retained development capture saves one selected-token vector per
case/condition. The resulting matrix is only 40 x 1536; the frozen train
partition would contain only 32 rows. That is underdetermined and is not an
adequate basis for a publication claim about a trained 1536-dimensional SAE.
It may be used for model-independent plumbing tests, but it must not be promoted
as trained-SAE scientific evidence.

The previously reported full-token activation archive (SHA-256
`7890212a8e7a4eb099be86bc572cd6172fd1c45b839f695e56e6ba4a46e97b21`)
is not present in the repository or the authorized retained-result folders.
The prospective protocol therefore requires that archive, at least 10,000
training rows, and exact hash verification before training.

## Second-model state

The canonical generic qualification runner is implemented and fail-closed. No
second model is currently authorized: the committed candidate file deliberately
contains placeholders and no human approval. The prior supporting manifest's
Phi-3 suggestion has revision `unknown` and is not a freeze. Qwen2.5-0.5B is
ineligible as successful generalization evidence because it already failed the
balanced qualification condition.

The next human decision must select a distinct compatible model and immutable
revision. Only then may a reviewed candidate config be created and approved.
No weights have been downloaded and no second-model result has been claimed.

## Next gate

Review `configs/experiments/qwen_sae_training_freeze_v1.json`. Its exact hash is
reported in `docs/SAE_TRAINING_FREEZE_V1_REVIEW.md`. Training remains forbidden
until the exact protocol is human-approved and the declared full-token archive
is supplied and hash-verified.
