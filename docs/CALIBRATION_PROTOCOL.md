# Mechanistic Calibration Protocol

## Purpose and boundary

Calibration asks whether AETHER's causal instrumentation reproduces externally documented behavior before it is applied to the novel sender-message-receiver setting. It is methodology validation, not an AETHER novelty claim.

## Tracr: known-structure sanity check

Tracr compiles a symbolic RASP program into a Haiku/JAX transformer. The pinned official `make_reverse(rasp.tokens)` example supplies known program and compiler structure. We compare symbolic reversal with decoded transformer output and record the compiler graph, residual shapes, layer outputs, and attention-logit shapes.

This does not validate PyTorch/Qwen hooks. No Tracr intervention was attempted because building a parallel JAX/Haiku intervention layer would exceed the value of this secondary track. Tracr runs only in `.venv-tracr`.

## IOI: primary real-model causal calibration

GPT-2 Small IOI is an externally documented circuit with published causal intervention evidence. The canonical metric is `logit(IO) - logit(subject)` at the next-token answer position.

The dataset contains 24 fixed, unsampled BABA/ABBA-style prompt pairs. Names come from the original released IOI name set, are required to be one GPT-2 token with leading space, and every clean/corrupted pair has identical token length. Corruption changes the repeated subject token to the indirect-object name while preserving the prefix and name positions.

Head output `z` is captured immediately before GPT-2 attention `c_proj`. Clean per-head output at the answer position replaces the corresponding corrupted output. The tested known subset is the three highest-listed name-mover heads in the pinned original circuit file: `(9,9)`, `(10,0)`, `(9,6)`. Controls contain the same number of heads, exclude every published circuit head, and are sampled with seeds 11, 22, and 33.

Normalized recovery is:

`(patched_logit_difference - corrupted_logit_difference) / (clean_logit_difference - corrupted_logit_difference)`

Before causal execution, acceptance required baseline accuracy at least 70%, passive fp32 hooks within `rtol=1e-5, atol=1e-6` with identical argmax predictions, and known-group mean recovery exceeding matched-random mean by at least 0.10.

## What this validates

- Tracr: known symbolic/compiler structure corresponds to compiled transformer behavior.
- IOI: real-model passive capture, per-head activation patching, metric calculation, controls, cleanup, and reproducible artifacts behave as expected.

## What this does not validate

Neither track proves the AETHER DCMG hypothesis, bridge verification protocol, or a sender-message-receiver mechanism. The IOI result is a calibration outcome and must not be presented as new circuit discovery.
