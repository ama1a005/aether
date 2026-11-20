# Qwen SAE training freeze v1.3 — execution-semantics review

## Why review is required

The first v1.2 training attempt produced ten epochs for seeds 11 and 22. Both
processes then raised `seed produced no sparsity-eligible checkpoint`; seed 33
never started. This is not a CUDA, RAM or download failure. The trainer counted
every epoch before the first eligible checkpoint as stale and applied the
ten-epoch patience limit, despite the frozen maximum of 100 epochs.

Because epoch metrics have now been observed, the behavior must not be changed
silently. The retained histories and checkpoints remain part of the audit trail.

## What v1.3 changes

Only execution and negative-result semantics change:

1. Early stopping cannot occur before the first sparsity-eligible checkpoint.
2. A seed continues to the first eligible checkpoint or epoch 100.
3. After eligibility, the unchanged patience of ten monitors eligible
   checkpoint-selection reconstruction error.
4. Seeds 11 and 22 resume their exact epoch-10 model and optimizer states.
5. Seed 33 runs fresh even if the first two seeds are scientifically rejected.
6. No eligible checkpoint after epoch 100 becomes an explicit seed rejection,
   not an exception that destroys the final evidence bundle.
7. All three seed summaries are required. Audit capture occurs only if at least
   one seed is eligible.
8. A completed all-seed rejection produces an independently verifiable FAIL
   bundle.

## What does not change

The following remain exactly frozen:

- Qwen model, revision, component and tokenizer;
- WikiText source revision, file hash, token order and partitions;
- normalization;
- 1536→3072 linear ReLU SAE architecture;
- Adam, learning rate `0.0003`, batch size `256`, L1 coefficient `0.0001`;
- seeds 11, 22 and 33;
- active-fraction interval `[0.001, 0.2]`;
- reconstruction threshold `0.1`;
- dead-feature threshold and mean-vector baseline;
- selection rule;
- AETHER development audit cases;
- validation/test locks; and
- reconstruction/sparsity-only claim boundary.

The observed active fractions near `0.71` are not used to loosen the gate or
retune L1. The run may still end in a valid negative result after 100 epochs.

## Evidence handling

- Preserve existing epoch histories and epoch-10 checkpoints.
- Resume only if model state, optimizer state, epoch, seed, protocol identity
  and history prefix all match.
- Do not restart seeds 11 or 22 from random initialization.
- Do not describe the current partial attempt as SAE rejection or acceptance.
- Export PASS and FAIL bundles with the same provenance and hash requirements.

## Human checklist

- [ ] The change is limited to execution/terminal semantics.
- [ ] No scientific threshold or hyperparameter is weakened.
- [ ] The retained epoch-10 checkpoints must be resumed exactly.
- [ ] Seed 33 must run regardless of scientific rejection of the first pair.
- [ ] No eligible seed is an admissible negative result, not a crash.
- [ ] Audit/validation/test data cannot tune training.
- [ ] Protected split counts remain zero.

## Approval form

After independently hashing the exact amendment file:

```text
I approve Qwen SAE training freeze v1.3 amendment SHA-256 <EXACT_HASH>
```

No trainer or notebook change is authorized before that exact-hash approval.
