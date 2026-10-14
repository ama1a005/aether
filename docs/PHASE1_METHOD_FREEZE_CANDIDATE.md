# Phase-1 Method-Freeze Candidate

**Status:** candidate for review; **DO NOT FREEZE** on the current development evidence. Validation and test remain unopened.

## Research question

Can AETHER identify localized, case-specific internal causal contributions on both sides of an already-causal serialized message mediator, rather than merely demonstrating that broad hidden-state replacement can overwrite a decision?

## Primary claim to test

`DCMG adds intervention-validated internal localization on both sides of an already-causal serialized message mediator.`

The current hardening run falsifies support for this claim on development: no selected sender or receiver site survived all frozen specificity criteria. The claim must not proceed to validation without a reviewed methodological revision.

## Secondary claims

1. Whole-message replacement is a robust causal positive control for the mediator-to-outcome edge.
2. Selected sender and receiver regions are development causal responders under broad activation replacement, without implying case-specific localization.
3. Identity clean-to-clean patching establishes intervention non-interference only; it is not benign-utility or defense-utility evidence.
4. Receiver-only activation replacement is an internal baseline, not evidence that DCMG improves behavioral repair over message replay.

## Datasets

The causal substrate is the fixed synthetic **AETHER positive-control causal substrate** with **AETHER deterministic tool-output manipulation**. MCPTox and TAMAS are excluded from causal hardening. MCPTox raw records are not redistributed pending license resolution; TAMAS native/provider evaluation is deferred.

## Development / validation / test splits

The frozen registry contains 16 development, 4 validation, and 4 test pairs; split hash `c510bc406b168a2639ac49f8199a7f78ba2f318893fce7be2d6c3b254266a39e`. Discovery and hardening used only the 16 development pairs. Validation and test are locked until human approval of a revised method.

## Model / revision

`Qwen/Qwen2.5-0.5B-Instruct` at revision `7ae557604adf67be50417f59c2c2f167def9a775`, deterministic greedy inference, float32 CPU.

## Mediator schema

The typed serialized `MediatorMessage` is the sole sender-to-receiver bridge. Sender interventions must regenerate it. Receiver interventions must hold the applicable clean or attacked serialized message byte-identical.

## Outcome metric

Primary continuous outcome is the unclipped receiver escalation-margin recovery `(intervened - attacked) / (clean - attacked)`, with raw margins retained. Sender decision-code changes, mediator hashes/fields, outcome codes, per-pair effects, consistency fractions, and deterministic bootstrap intervals are secondary measurements.

## Candidate discovery method

The historical coarse pass scanned the predeclared 18 module sites per role at layers 0, 5, 9, 14, 18, and 23. Its permissive results are now called **development causal responders**, not supported internal causal sites.

## Refinement method

Hardening was limited to sender `L14.block_output`, `L14.attention_output`, `L18.block_output` and receiver `L23.block_output`, `L18.block_output`, `L14.attention_output`. No all-layer rescan was allowed. Head refinement was not performed because the adapter does not expose scientifically valid pre-projection per-head tensors; post-projection slicing is prohibited.

## Intervention operators

Paired clean-to-attacked activation replacement tests rescue; paired attacked-to-clean replacement tests induction. Clean-execution zero ablation supplies operator-sensitivity/necessity-like evidence only. Formal global necessity or sufficiency is not claimed.

## Token-position policy

The primary position is the last aligned prompt token. For the predeclared top site per role, comparisons use the first stable cross-condition differing token and structurally equal token index 1. Unequal shapes or unstable/invalid alignment fail closed.

## Causal support criteria

A supported internal causal candidate must simultaneously have median rescue at least `0.5`; rescue above `0.25` in at least `75%` of pairs; median induction at least `0.5`; induction above `0.25` in at least `75%` of pairs; median rescue at least `0.2` above matched controls; at least `0.2` above the irrelevant-position effect when applicable; and at least `0.2` above deterministically shuffled clean-source activation. All effects must have the expected raw direction. These thresholds were frozen before the hardening run and must not be relaxed in response to its null result.

## Baselines

Whole-clean-message rescue and trace-level clean-message replay each recover `1.0` and remain the behavioral standard to beat. Attacked-message induction is `1.0`; decision-code-only mean normalized recovery is `0.6410677455385805`. Receiver-only activation replacement is reported separately as localization evidence and does not outperform message repair.

## Control procedure

Use the once-sampled 12 deterministic controls (seeds 101–112), matched where possible on role, component type, position, direction, and operator. Preserve the randomly selected strong control `sender.L23.block_output` with rescue `1.0`. Use a deterministic cyclic shift with no self-maps for shuffled-source activation. Never resample controls based on their outcomes.

## Query budget

The completed hardening budget was 67 model queries: 2 sender forwards, 23 sender generations, and 42 receiver forwards. Any revised development method requires a new bounded task and a newly frozen budget before execution.

## Statistical plan

Report raw paired effects, means, medians, standard deviations, ranges, deterministic bootstrap mean 95% intervals, consistency counts, and the fixed matched-control distribution. No adaptive p-value search is permitted. Locked validation/test inference requires a separate reviewed plan.

## Benign-utility plan

Do not infer benign utility from identity patches. After a deployable intervention is selected, evaluate clean accuracy, raw-margin change, mediator validity, collateral output changes, and runtime/query overhead on the locked evaluation plan.

## Failure / falsification conditions

The primary localization claim fails if either side lacks a surviving candidate; shuffled activation performs comparably to paired activation; broad or late-block controls perform comparably; bidirectional effects fail; relevant-position effects do not exceed irrelevant positions; serialized messages change during receiver interventions; or message replay remains the only robust causal level. The completed development run triggered the first three conditions.

## Exclusions

No validation/test access, final candidate selection, RL, Phase 2, model or benchmark download, paid API use, all-layer rescan, post-hoc threshold change, arbitrary head slicing, or mutation of the positive-control task is allowed at this checkpoint.

## Results that are not allowed to change the method

Strong random controls, null induction, shuffled-source equivalence, unfavorable ablation sensitivity, perfect message replay, and other negative results must remain visible. They cannot trigger resampling, candidate substitution, threshold relaxation, split access, or retroactive position/operator changes.

## Development decision

The present candidate is documented but not ready to freeze. The next bounded work should redesign internal granularity/operator semantics on development, freeze that revision before execution, and repeat specificity hardening. Validation and test must remain closed.
