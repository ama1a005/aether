# QCI-2 method-freeze v2.3 algorithm-completion review gate

Status: `AWAITING_HUMAN_REVIEW`

Candidate amendment:
`configs/phase1_core/qci2_method_freeze_v2_3_amendment.yaml`

SHA-256:
`5e8fc93feeb04227462769e0ebdb9f8e7aa759b9cbca118c61c0ee4faf421c06`

V2.3 changes no evidence, candidate, metric, threshold, split or budget. It
prospectively supplies the algorithm details that the approved proposal names
but does not determine: overlap-safe starts and transitions, deterministic tie
breaks, matched-random reference and sampling, and exact flat-PPO environment,
hyperparameters, checkpoint selection and reload behavior.

## Human checklist

- [ ] I reviewed the exact amendment bytes and SHA-256 above.
- [ ] I approve four legal maximal masks as full-search/PPO episode starts.
- [ ] I approve the exact greedy, beam-width-two and receiver-only traversal.
- [ ] I approve matched random against the same-seed greedy terminal mask using
      a fresh cache and exact region counts.
- [ ] I approve the declared masked node-removal PPO configuration, reward,
      checkpoint selection and fresh-cache deterministic reload.
- [ ] I confirm audit, validation and test remain forbidden.

No decision artifact may be generated without an explicit human approval that
quotes the exact SHA-256.
