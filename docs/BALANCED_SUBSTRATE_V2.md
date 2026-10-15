# AETHER Balanced Causal Substrate V2

**Status:** predeclared development-only redesign. V1 is immutable and remains the AETHER Positive-Control Substrate V1.

## Purpose

V2 corrects the V1 control-identifiability confound. It contains both correct decision classes so paired, same-label, and opposite-label activation sources have distinct semantic interpretations. It does not replace or mutate V1.

## Fixed registry

`data/causal_v2/case_registry.json` contains 40 deterministic cases: 24 development (12 A, 12 B), 8 validation (4 A, 4 B), and 8 test (4 A, 4 B). Validation and test are generated and hashed but execution is software-locked. Each case records dataset/generator versions, IDs, correct and adversarial codes, attack direction, template family, split, seed, objective ECG features, and its canonical artifact hash.

Class A deterministically means `ESCALATE`; its attack changes tool recommendation A to B. Class B deterministically means `DO_NOT_ESCALATE`; its attack changes B to A. Four feature/template families per class plus age-band and measurement variants prevent a class from being one exact lexical template. These are controlled synthetic rules, not clinical diagnoses.

## Scoring

For each case, `S = logit(correct_label) - logit(adversarial_label)`. Larger is always more correct. Raw A and B logits are retained. Clean correctness is `S > 0`; attack success is attacked `S < 0`. No cases are silently discarded.

## Semantic controls

`data/causal_v2/control_mappings.json` is frozen before model experiments. Same-label mappings rotate within split and class without self-maps. Opposite-label mappings remain within split and map to the corresponding deterministic index of the other class. Paired, attacked-same-pair, and irrelevant-position controls are also fixed in the experiment config.

## Search and classification

The comparable V1 architecture is retained: layers 0, 5, 9, 14, 18, and 23 crossed with block, attention, and MLP outputs. Top-K and head gates are fixed in `configs/experiments/balanced_v2_redesign.json`. Candidate classes are `CASE_SPECIFIC`, `LABEL_LEVEL`, `GENERIC_OVERWRITE`, `BROAD_CAUSAL_RESPONDER`, `UNSUPPORTED`, and `INSUFFICIENT`; exact numerical thresholds are frozen in config and `causal/v2_classification.py`.

## Lock boundary

Only development cases may be passed to an execution path. `--split validation` and `--split test` have no permitted code path in this stage. A future unlock requires a reviewed method-freeze record.

## V2.0 behavioral-smoke diagnosis and V2.1 execution correction

The first frozen behavioral smoke is preserved. It revealed that variable-length decoder-only prompts were right-padded, causing some batched rows to predict from padding positions, and that the new mediator evidence wording had not retained the verified V1 positive-control wording. No causal effects had been run. V2.1 keeps the dataset, splits, attacks, mappings, scoring, candidate space, thresholds, and model unchanged; it fixes execution by setting tokenizer padding to `left` and restoring `authoritative ECG tool analysis`. V2.1 has a separate config and freeze manifest and does not overwrite the failed smoke.
