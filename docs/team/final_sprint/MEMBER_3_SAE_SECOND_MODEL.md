# Member 3: trained SAE and second-model qualification

**Branch:** `m3/mech-interventions`
**Deadline:** 20 November 2026, 10:30 Asia/Kolkata

## Mission and boundaries

Close `trained_sae_qwen_evaluation` using a genuinely trained,
provenance-locked SAE on real Qwen activations. Prepare and execute second-model
qualification only under its dependency/freeze rules. Do not edit attack labels,
CORE-03, validation/test protocols or contracts.

## Relevant paths

- SAE loader: `causal/interventions/sae.py`
- canonical evaluator: `experiments/phase1/qwen_sae_evaluation.py`
- config/notebook: `configs/experiments/qwen_sae_development.yaml`,
  `notebooks/aether_qwen_sae.ipynb`
- prior training code: `experiments/supporting_nov19/sae/`
- second-model canonical runner:
  `paired_trace/run_secondary_model_qualification.py`
- prior helper: `experiments/supporting_nov19/second_model/`

Reconcile helpers with canonical entry points; do not introduce a third
checkpoint format or qualification path.

## Step 1: branch and baseline

```bash
git fetch origin --prune
git switch lm
git pull --ff-only origin lm
git switch -c m3/mech-interventions
python -m pytest tests/unit/test_sae_checkpoint.py \
 tests/unit/test_qwen_sae_evaluation.py \
 tests/unit/test_support_nov19_sae.py \
 tests/unit/test_support_nov19_guards.py \
 tests/unit/test_secondary_model_qualification.py \
 tests/unit/test_support_nov19_second_model.py \
 tests/unit/test_model_adapter.py -q
```

Create `docs/handoffs/mechanistic/FINAL_SPRINT_START.md` with available model
cache, activation files, RAM/disk/GPU, hashes, tests and missing resources.

## Step 2: locate and validate activation data

Do not assume an old reported archive exists. Search authorized storage and
current development-capture manifests. For each candidate archive:

1. record external location without hard-coding it in Git;
2. record size and SHA-256;
3. verify pinned Qwen model/revision;
4. verify development-only split;
5. verify component IDs, shapes, dtype and token-position policy;
6. verify exact case IDs and absence of duplicates/missing rows;
7. define train/audit partition before training;
8. reject synthetic/mock/reconstructed tensors as scientific input.

If the reported 4.87 GB archive is absent or its hash fails, record the blocker.
Never fabricate a replacement file.

## Step 3: prospectively freeze SAE training

If no compatible trained checkpoint exists, create a versioned protocol that
freezes before training:

- activation archive hash and component;
- model/revision and hidden width;
- train/audit case IDs;
- train-only normalization;
- architecture, feature count and activation;
- optimizer, learning rate, batches, steps/epochs;
- sparsity coefficient and complete loss;
- seeds and checkpoint-selection rule;
- reconstruction threshold;
- dead-feature and sparsity metrics;
- early stopping and compute budget;
- required artifacts/failure states;
- validation/test lock;
- exact human approval.

Add fail-closed model-independent tests. Publish exact SHA-256 and stop. A human
owner—not the coding agent—must approve it.

## Step 4: train and package the SAE

After approval:

1. pass model-independent preflight;
2. train only on frozen training activations;
3. evaluate reconstruction/sparsity on untouched development audit activations;
4. checkpoint atomically at declared intervals;
5. preserve seed, loss history and environment;
6. export canonical `metadata.json` and `weights.npz`;
7. record code/model/archive/component/normalization/checkpoint hashes;
8. load with `load_sae_checkpoint` using exact expected identifiers;
9. reject shape mismatch, NaN/Inf, normalization mismatch, excessive error or
   random/untrained weights.

Store large tensors/checkpoints outside Git and retain immutable hashes.

## Step 5: real-Qwen SAE evaluation

Require approved training protocol, verified checkpoint, pinned snapshot, clean
Git, development-only cases, output safety and resources before model access.
Capture real activations, validate reconstruction and report sparsity/dead
features. Execute feature interventions only if prospectively authorized; if the
frozen protocol permits reconstruction only, do not make a causal claim.

Preserve raw per-case rows and errors, independently verify, and atomically
ingest into `results/phase1/sae/qwen15b`.

## Step 6: second model

Preparation can begin now, but the registry places evidence promotion after the
once-only primary-model test.

1. Audit candidates for license, adapter support, memory and tokenizer labels.
2. Do not reuse a model with a binding balanced-qualification failure.
3. Freeze exact model/tokenizer revisions, dtype/device, prompts, cases,
   thresholds, seeds, instrumentation sites and failures.
4. Obtain exact human approval before access.
5. Implement typed model-specific adapters without weakening Qwen contracts.
6. Run the full behavioral, rescue/induction, hook non-interference and
   activation-persistence gates.
7. Preserve every raw row and denominator.
8. Independently verify the complete bundle.
9. Never call a load test or partial run “second-model qualification.”

## Required final tests

```bash
python -m pytest tests/unit/test_sae_checkpoint.py \
 tests/unit/test_qwen_sae_evaluation.py \
 tests/unit/test_support_nov19_sae.py \
 tests/unit/test_support_nov19_guards.py \
 tests/unit/test_secondary_model_qualification.py \
 tests/unit/test_support_nov19_second_model.py \
 tests/unit/test_model_adapter.py \
 tests/integration/test_hook_non_interference.py -q
```

## Definition of done

- Activation input is real, hash-verified and split-safe.
- SAE protocol predates training and has human approval.
- Checkpoint provenance and reconstruction acceptance verify.
- Real SAE bundle passes, or the precise resource blocker is documented.
- Second-model protocol is frozen and, after dependency clearance, fully
  qualified or retained as a genuine negative/incomplete result.

