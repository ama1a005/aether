# AETHER Project State

**Last verified:** 2026-10-14
**Current phase:** Phase 1, causal-specificity hardening and method-freeze review
**Status:** Hardening complete; no internal candidate survived; method freeze not recommended

## Completed

- CPython 3.11.9 repository-local environment verified.
- Editable installation from `pyproject.toml` completed without global packages.
- Resolved dependency snapshot recorded in `requirements-lock.txt`.
- Full suite verified after manifest hardening: 85 passed, 0 failed, 0 skipped.
- All documented target, attack, P3, P4, and end-to-end smokes passed.
- Invalid build backend, undeclared pandas dependency, and missing `Any` import fixed.
- Run-manifest builder, validation, artifact hashing, timing fields, atomic writer, CLI, tests, and Stage-0 manifest added.
- Minimal GitHub Actions Windows/Python 3.11 workflow added.
- Stage-0 checkpoint commit: `1b52b565e346e520cc474ac61eeca5a09c5896ac`.
- Hardware baseline: i5-12500H (12 cores/16 threads), 15.67 GiB RAM, RTX 2050 4 GiB; repository PyTorch is CPU-only.
- Qwen2.5-0.5B-Instruct is pinned to `7ae557604adf67be50417f59c2c2f167def9a775`; its 988,097,824-byte weight file matches the publisher SHA-256.
- Deterministic CPU inference, passive-hook non-interference, full-prompt activation capture/reload, and one layer-12 MLP zero intervention are verified.
- Real-enabled full suite: 88 passed, 0 failed, 0 skipped; one non-fatal cache warning.
- Real-model instrumentation checkpoint: `1a7f3ad` (`feat: add verified real-model activation instrumentation`).
- Mechanistic calibration checkpoint: `28ecd11` (`test: add mechanistic calibration with Tracr and GPT-2 IOI`).
- Known-structure Tracr reverse calibration passed 3/3 fixed cases at pinned revision `9ce2b8c82b6ba10e62e86cf6f390e7536d4fd2cd` in isolated `.venv-tracr`.
- GPT-2 Small IOI calibration at revision `3fe9a169f57f3ca0cac0b9133351644193b9dd3c`: 24/24 baseline accuracy, passive max logit delta `0.0`, known-head recovery `0.3880`, matched-random mean `0.0026`.
- Calibration-enabled full suite: 96 passed, 0 failed, 0 skipped; one known non-fatal cache warning.
- Frozen paired-case registry contains 16 development, 4 validation, and 4 test cases; only development was executed (split hash `c510bc406b168a2639ac49f8199a7f78ba2f318893fce7be2d6c3b254266a39e`).
- Paired real-model development run retained all 16/16 clean/attacked attempts: 16 clean-correct, 16 attack-success, 0 invalid, and 0 excluded.
- Whole-message rescue and attacked-message induction both produced a mean fraction of `1.0`; the decision-code-only patch produced unclipped mean recovery `0.6410677455385805`.
- BVP Level 1 (`M -> Y`) is accepted. Exploratory Level 2 (`A -> M`) is rejected because the sender patch did not change the message; Level 3 (`B -> Y`) is rejected because its effect was in the wrong direction. The full distributed path is not verified.
- Paired-foundation gated suite: 109 passed, 0 failed, 0 skipped; P1, P2, P3, P4, end-to-end, aggregate, and real-instrumentation smokes all passed.
- BVP foundation checkpoint: `b531b7d` (`feat: add real paired traces and bridge verification foundation`).
- Terminology corrected: the ECG attack is **AETHER deterministic tool-output manipulation** and the dataset is the **AETHER positive-control causal substrate**, not MCPTox-style poisoning.
- Official MCPTox source pinned at `f85189f9`; its local release contains 485 poisoned-tool records. A deterministic 20-record released-response smoke produced 2 `Success`, 14 `Failure-Ignored`, and 4 `Failure-Direct Execution` labels for released `Qwen3-8b-No-Think` outputs (ASR `0.10`). This is not a local Qwen-0.5B run.
- TAMAS pinned at `545c112a`; adapter loaded all 300 adversarial records and serialized a 10-record smoke. Native AutoGen/CrewAI execution was not run.
- Coarse development search scanned 18 frozen sites per role. Four sender sites and ten receiver sites met the predeclared exploratory support rule. Best sender sites recovered all 16 mediator decisions; best receiver site `receiver.L23.block_output` recovered all 16 scores (`1.0` normalized recovery).
- Message-only and trace-level clean-message replay recovery remain `1.0`; the strongest simple baseline is therefore not hidden. The internal results are exploratory development candidates, not a full distributed-mechanism result.
- Standardized-anchor/discovery gated suite: 121 passed, 0 failed, 0 skipped; one known non-fatal cache warning.
- Standardized-anchor/discovery checkpoint: `34848c1` (`feat: add standardized anchors and development causal discovery`).
- Specificity protocol/config were frozen before execution at SHA-256 `8a7c75827064e4ff847742d808f307478acba09cf925047ca0029291a83b7049` and `85d8539e4ab6facb4d60d912d7a3402b12e98485e23a6b636be63d17e6223f1d`.
- Development-only hardening completed 67 queries in 698.42 s. All six selected internal sites were rejected. Every site failed shuffled-source separation; sender L14 block/attention additionally failed induction, receiver L18 block failed median rescue, and receiver L14 attention failed all non-position criteria.
- Earlier coarse hits are now **development causal responders**, not supported internal causal candidates. The retained randomly selected `sender.L23.block_output` control also had rescue `1.0`.
- Message rescue and trace replay remain `1.0`; Level 1 mediator causality is the only robust current causal level. Identity patching is intervention non-interference, not benign-utility preservation.
- `docs/PHASE1_METHOD_FREEZE_CANDIDATE.md` records recommendation **DO NOT FREEZE METHOD**. Validation and test remain unopened.
- MCPTox raw released-response rows were removed from tracked artifacts and ignored pending license resolution; source hashes, subset IDs, aggregate metrics, and integration code remain.
- Hardening-complete gated suite: 126 passed, 0 failed, 0 skipped with real-model and calibration gates enabled; one known non-fatal `.pytest_cache` warning. P1, P2, P3, P4, end-to-end, aggregate 3/3, real instrumentation, MCPTox summary-only, and TAMAS adapter smokes passed.

## Partial or pending external verification

- The paired trust task uses a fixed synthetic ECG escalation substrate and AETHER deterministic tool-output manipulation; it is development evidence, not benchmark or deployment evidence.
- DCMG coarse discovery and specificity hardening are complete on development, but localized internal causality is unsupported. Remediation remains unstarted.
- Existing experiment entry points do not yet invoke the manifest writer automatically; the tested CLI records completed runs.
- The exact filename `ProjectDescription.md` is absent. `4_ProjectDescription.md` is the current additive-platform/DCMG/BVP document and remains untracked.
- CI uses the locally passing command but has not run on GitHub yet.

## Known issues

- `.pytest_cache` is inaccessible, producing one non-fatal warning.
- `py -3.11` is not available in the agent shell PATH.
- PowerShell execution policy blocks `.venv/Scripts/Activate.ps1`; direct interpreter invocation works.
- Benchmark registry pins and hashes remain `TBD` until later approved stages.

## Next proposed task

Current recommendation: after review, define a bounded development-only redesign of intervention granularity/operator semantics, freeze it before execution, and repeat specificity hardening. Do not open validation until a specific internal candidate survives or the Phase-1 claim is formally narrowed to mediator-level causality.
