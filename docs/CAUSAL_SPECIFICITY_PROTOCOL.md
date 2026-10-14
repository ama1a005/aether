# Causal Specificity Hardening Protocol

**Status:** predeclared development protocol; not a frozen Phase-1 method.

## Question

Are the development causal responses localized and specific, or does replacing broad hidden states across many layers generally rescue the decision?

The coarse-scan label “supported causal site” is reinterpreted as **development causal responder** until a site passes this protocol. Clean→clean self-patching is an **identity-patch/intervention non-interference control**, not benign-utility evidence for a deployable defense.

## Candidate and refinement space

The sender candidates are `L14.block_output`, `L14.attention_output`, and `L18.block_output`. The receiver candidates are `L23.block_output`, `L18.block_output`, and `L14.attention_output`. These are the frozen Pass-1 top three; no other layer is added after results are observed.

Each candidate receives paired clean→attacked rescue and attacked→clean induction at the last aligned prompt token. Sender interventions regenerate the message and rerun the unchanged receiver. Receiver interventions hold the serialized clean or attacked message byte-identical within their condition.

Position specificity is evaluated for the top sender (`L14.block_output`) and receiver (`L23.block_output`) sites at: the last prompt token, the first cross-condition differing token, and token index 1, which must be structurally identical. Any invalid alignment is recorded ineligible.

## Controls

Paired source activations are compared with a deterministic cyclic shift by one pair, never mapping a case to itself. The late-block generic-overwrite test compares paired and shuffled L23 clean activations and earlier matched block sites.

Twelve controls are sampled once with seeds 101–112. Each is matched on agent role, component type, decision position, rescue direction, and patch operator. The previously sampled strong random control `sender.L23.block_output` is retained and reported; it is not resampled.

Clean-execution zero ablation is the second operator for the six selected candidates. It is necessity-like sensitivity evidence only, not formal necessity. Paired replacement is rescue/sufficiency-like evidence only, not formal sufficiency.

## Metrics and stronger support

All normalized effects are unclipped and retain per-pair raw values. A **supported internal causal candidate** must satisfy every applicable condition:

1. median paired rescue ≥ 0.50;
2. at least 75% of pairs have rescue > 0.25;
3. median attacked-state induction ≥ 0.50;
4. at least 75% of pairs have induction > 0.25;
5. median rescue exceeds the matched-control median by ≥ 0.20;
6. for a position-tested site, decision-position rescue exceeds the irrelevant-position result by ≥ 0.20;
7. paired rescue exceeds shuffled-source rescue by ≥ 0.20;
8. raw effects move in the predeclared theoretical direction.

Means, medians, standard deviations, ranges, individual effects, consistency counts, and deterministic bootstrap intervals are reported. No development p-value gate is used.

## Stopping and head-level rule

Stop after top-three bidirectional testing, top-one-per-role position specificity, shuffled controls, twelve matched controls, and zero-ablation sensitivity. Do not rescan all layers. Head refinement occurs only if the parent attention site passes all criteria and semantically valid pre-projection per-head instrumentation exists. The current adapter exposes post-mixing attention-module output only, so head search is unavailable and must not be fabricated.

The message-only recovery of `1.0` remains the behavioral-repair standard. The proposed incremental-value claim is narrower: **DCMG adds intervention-validated internal localization on both sides of an already-causal serialized message mediator.** Validation and test remain unopened.
