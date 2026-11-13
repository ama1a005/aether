# QCI-2 method-freeze v2.2 accounting review gate

Status: `AWAITING_HUMAN_REVIEW`

Candidate amendment:
`configs/phase1_core/qci2_method_freeze_v2_2_amendment.yaml`

SHA-256:
`fed75de69761c504653026a8a919014ea40bca8f8efe1c2b2f1127206cfda03b`

## Why this amendment is required

The approved method defines two real executions for every evaluated mask:

1. attacked execution, used for rescue and signed faithfulness;
2. clean-to-clean identity execution, used for benign damage in raw A-minus-B
   logit-margin units.

Each condition requires four uncached sender autoregressive forwards and one
receiver forward for each of 16 cases. Therefore a complete mask evaluation
costs `16 * 2 * (4 + 1) = 160` forward steps. V2.1 counted only the attacked or
the benign condition, not both.

The corrected maximum is `160 baseline + 45 * 160 = 7,360` forward steps per
method and seed. Actual consumption must still be reported and may be lower.

## Exact change boundary

Changed only:

- conditions per mask evaluation: one to two;
- forward steps per mask evaluation: 80 to 160;
- maximum forward steps per method/seed: 3,760 to 7,360.

Unchanged:

- all QCI-1/QCI-2 evidence and results;
- the four internal candidates and two message candidates;
- mask and overlap semantics;
- five required methods and seeds 11/22/33;
- 32 unique-search-mask and 45 total-evaluation limits;
- objective, benign threshold, BVP rules and construct limitation;
- development-only split and all audit/validation/test locks.

## Human checklist

- [ ] I reviewed the exact amendment bytes at the SHA-256 above.
- [ ] I agree that attack and clean identity are distinct model executions.
- [ ] I approve 160 forward steps per complete 16-case mask evaluation.
- [ ] I approve a 7,360 maximum per method/seed, with actual use reported.
- [ ] I understand this approval authorizes implementation/execution only on
      the 16 development-discovery cases.

No approval decision artifact exists. Codex must not create one without an
explicit human decision quoting the exact SHA-256.
