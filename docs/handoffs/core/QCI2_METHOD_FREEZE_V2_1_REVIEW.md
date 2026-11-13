# QCI-2 method-freeze v2.1 accounting amendment — review request

The human-approved v2 proposal is preserved at SHA-256
`b15b660f3a5f7843e84d3612a8ec0a9434735da34d614c3645d3d5a2cc947d2c`.

During runner mapping, the implementation audit found that qualified sender
generation uses four uncached autoregressive forwards, not one generation-level
forward. Each case therefore costs four sender forwards plus one receiver
forward. Across 16 cases:

- one mask evaluation costs 80 model forwards;
- two-condition baselines cost 160 forwards;
- 32 search masks plus 13 reserved evaluations and baselines cost at most 3,760
  forwards per method and seed.

The amendment changes only the forward-step ceiling from 1,504 to 3,760 and the
associated per-mask/baseline accounting. It does not change candidates, masks,
overlap rules, methods, seeds, mask-call limits, thresholds, BVP rules, cases or
split access.

Human approval must reference the exact amendment SHA-256 printed by
`python -m causal.method_freeze`. No model execution is authorized until this
narrow correction is approved.
