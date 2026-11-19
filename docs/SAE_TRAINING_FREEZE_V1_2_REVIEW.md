# Qwen SAE training freeze v1.2 — pinned corpus revision correction

## Decision requested

Review
`configs/experiments/qwen_sae_training_freeze_v1_2_amendment.json` and approve
only its exact SHA-256.

SHA-256:
`fdc02d9542af6d6b54aad57da8facd21ba7ff07bf5286a0874fc7ded6418b238`

V1 and v1.1 remain immutable. V1.2 changes only the immutable repository commit
used to retrieve the already approved WikiText-2 raw training parquet.

## Observed blocker

The approved v1.1 revision
`de54f133ef530c2e9b46c532f95a01c446ff0f1d` returns HTTP 404 for
`wikitext-2-raw-v1/train-00000-of-00001.parquet`. A wildcard snapshot request
therefore returned zero files, and exact-file retrieval also failed. No corpus
tokens, activations, SAE checkpoint, audit result, validation case or test case
were produced.

## Prospective correction

- Dataset remains `Salesforce/wikitext`.
- Config remains `wikitext-2-raw-v1`.
- Split remains `train`.
- File remains `train-00000-of-00001.parquet`.
- Revision changes to the immutable commit that added the parquet:
  `b08601e04326c79dfdd32d625aee71d232d685c3`.
- The exact source file must hash to
  `e83889baabc497075506f91975be5fac0d45c5290b6b20582c8cd1e853d0c9f7`.

The notebook must download exactly that file, verify its SHA-256 before reading
it, and retain the hash in the corpus-source manifest.

## Unchanged scientific method

The following remain exactly as approved in v1/v1.1:

- Qwen2.5-1.5B-Instruct model and tokenizer revision;
- receiver layer-22 attention-output capture;
- float32 dual-T4 capture;
- repository-order text selection;
- empty-row removal;
- pinned-tokenizer tokenization with EOS separators;
- 65,536 selected tokens;
- 57,344 training tokens;
- 8,192 checkpoint-selection tokens;
- 256-token blocks;
- SAE architecture, optimizer, loss and seeds 11/22/33;
- checkpoint-selection rule;
- four frozen AETHER development-audit cases;
- acceptance thresholds;
- zero validation/test access;
- reconstruction/sparsity-only claim boundary.

## Reviewer checklist

- [ ] The v1.1 URL failure is correctly documented.
- [ ] The new revision is immutable and contains the declared parquet.
- [ ] The exact parquet SHA-256 is frozen before execution.
- [ ] No case, token count, seed, threshold or model setting changes.
- [ ] No validation or test access is opened.
- [ ] No result was observed before this correction.
- [ ] The independently recomputed v1.2 proposal hash matches the requested hash.

Approval must use this form:

```text
I approve Qwen SAE training freeze v1.2 amendment SHA-256 <EXACT_HASH>
```
