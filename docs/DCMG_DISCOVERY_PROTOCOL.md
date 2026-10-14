# DCMG Development Discovery Protocol

## Frozen search space

The authoritative registry is `configs/causal_candidates/qwen2_5_0_5b_phase1_coarse.json`, frozen before the scan. For each logical role it contains layers 0, 5, 9, 14, 18, and 23 crossed with decoder-block, attention-module, and MLP outputs. Attention-module outputs are not described as individual heads.

The intervention is paired clean activation patching into the attacked execution at the equal-length, structurally corresponding last prompt token. Sender patches occur during the initial autoregressive generation step, after which the one-token mediator is regenerated. Receiver patches hold the attacked serialized mediator byte-identical. Any length/position mismatch is ineligible and fails closed.

## Coarse-to-fine and controls

Pass 1 evaluates all 18 sites per role. Top-K is fixed at 3 by median development causal effect. Sender ranking uses decision-field recovery followed by downstream recovery; receiver ranking uses normalized outcome recovery. Matched-control identities are sampled once from the non-top-K registry using seeds 11, 22, and 33. Pass 2 refinement and head-level Pass 3 are not executed in this stage.

Association norms are stored separately and cannot support edges. The historical permissive rule identified **development causal responders**: sender response required the regenerated mediator hash to change and its decision code to recover toward clean; receiver response required positive median normalized recovery and positive mean raw logit-margin movement. These labels are not supported internal causal candidates. Promotion requires the stronger bidirectional, matched-control, position, and shuffled-source criteria frozen in `docs/CAUSAL_SPECIFICITY_PROTOCOL.md`.

Normalized recovery is `(patched - attacked) / (clean - attacked)`, unclipped, with the existing `1e-6` denominator guard. Per-pair effects, mean, median, standard deviation, range, and deterministic bootstrap mean intervals are retained.

Query accounting separates sender forwards, sender generations, and receiver forwards. Development is the only permitted split. Validation and test access is rejected by software guards.

The specificity run found no promoted internal candidates. In particular, shuffled clean activations matched paired rescue at every selected sender site and at the strongest receiver sites, so the coarse replacement effects are insufficiently case-specific. Historical artifacts are preserved; this paragraph corrects their current interpretation.
