# CORE-02 parallel Kaggle execution guide

## What remains unchanged

This is the approved QCI-2 v2.4 scheduling-only execution. It runs the same
Qwen revision, development-discovery cases, legal masks, five methods, seeds,
budgets, evaluator and thresholds as the original CORE-02 notebook. It only
places each frozen seed on a separate worker. A shard is not final evidence.
Only the strictly merged and independently verified 15-run bundle can be
ingested.

Each friend must use their own Kaggle account in accordance with Kaggle's terms.
Do not exchange passwords, sessions or API credentials.

## Assignment

| Worker | Notebook | Starting state | Required final file |
|---|---|---|---|
| Owner / friend 1 | `aether_qwen_core02_seed11.ipynb` | Attach the existing `aether-core02-checkpoint.tar.gz` | `aether-core02-seed11-results.tar.gz` |
| Friend 2 | `aether_qwen_core02_seed22.ipynb` | Fresh; attach no CORE-02 checkpoint | `aether-core02-seed22-results.tar.gz` |
| Friend 3 | `aether_qwen_core02_seed33.ipynb` | Fresh; attach no CORE-02 checkpoint | `aether-core02-seed33-results.tar.gz` |

Do not divide the methods between workers. Matched-random depends on the
same-seed greedy result, and every seed shard must contain all five methods.

## Kaggle instructions for every worker

1. Create a new Kaggle notebook and use **File > Import Notebook** to upload the
   assigned `.ipynb` file from this repository.
2. Enable Internet in notebook settings. A CPU session is the frozen execution
   configuration; GPUs do not accelerate this CPU-float32 protocol.
3. For seed 11 only, upload the existing checkpoint tar as a private Kaggle
   dataset and attach that dataset to the notebook. Seeds 22 and 33 must not
   attach it.
4. Select **Run All**. Do not edit the seed, commit, model revision, cases,
   budgets or commands.
5. The long execution cell prints one line after every newly completed mask.
   Kaggle working files will contain a checkpoint tar refreshed after every
   completed mask:
   - seed 11: `aether-core02-checkpoint.tar.gz`
   - seed 22: `aether-core02-seed22-checkpoint.tar.gz`
   - seed 33: `aether-core02-seed33-checkpoint.tar.gz`
6. If a session stops, save that checkpoint tar as a private Kaggle dataset,
   attach it to a fresh session running the same notebook, and run all cells.
   Completed masks are reused; an interrupted, incomplete mask is safely rerun.
7. Completion is valid only when the last cell prints the independent shard
   verifier PASS and a SHA-256 for the final results archive.
8. Download the required `*-results.tar.gz` file and retain the displayed hash.
   Do not rename, edit or recompress its contents.

## Failure rules

- A foreign-seed or ambiguous checkpoint stops before model execution.
- More than one attached checkpoint stops execution.
- A source commit, amendment, model revision, preflight or split mismatch stops
  execution.
- A partial checkpoint is progress recovery, not evidence and must not be fed
  to the merger.
- Never fill missing files or numbers manually.

## Merge after all three final archives return

Place the three archives in separate directories and extract each without
editing its contents. From the repository Python 3.11 environment run:

```powershell
python -m scripts.verify_qci2_matched_search_shard <seed11-extracted-directory>
python -m scripts.verify_qci2_matched_search_shard <seed22-extracted-directory>
python -m scripts.verify_qci2_matched_search_shard <seed33-extracted-directory>

python -m scripts.merge_qci2_matched_search_shards `
  --shard <seed11-extracted-directory> `
  --shard <seed22-extracted-directory> `
  --shard <seed33-extracted-directory> `
  --output results-staging/core02-merged

python -m scripts.verify_qci2_matched_search_bundle results-staging/core02-merged
```

The merger rejects missing seeds, duplicate method/seed results, duplicate raw
mask evaluations, mixed provenance, altered inventories and protected-split
access. After it passes, use the existing atomic CORE-02 ingester; do not copy
the merged directory into the evidence tree manually.
