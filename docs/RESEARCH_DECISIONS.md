# Research Decisions

## RD-001 — Python baseline

- **Date:** 2026-10-11
- **Decision:** Phase 1 uses CPython 3.11; Python 3.14 is excluded unless a later documented decision changes this.
- **Reason:** The complete baseline passes on 3.11.9 and the project request freezes 3.11.

## RD-002 — Dependency management

- **Date:** 2026-10-11
- **Decision:** `pyproject.toml` is authoritative for direct dependencies and editable installation; `requirements-lock.txt` is the resolved Stage-0 snapshot.
- **Reason:** The repository already used PEP 621 metadata; another hand-maintained direct-dependency format would drift.

## RD-003 — Manifest contract

- **Date:** 2026-10-11
- **Decision:** Manifests are additive infrastructure in `experiments/manifest.py`; frozen shared contracts remain unchanged.
- **Reason:** Reproducibility metadata is required, but changing `contracts/` requires separate approval.

## RD-004 — Stage-0 scope

- **Date:** 2026-10-11
- **Decision:** No model, benchmark, RL, or new DCMG experiment occurs during Stage 0.
- **Reason:** The verified baseline must precede scientific expansion.

## RD-005 — Explicit manifest identity

- **Date:** 2026-10-11
- **Decision:** Serious-run manifests require nonblank model, tokenizer, dataset, version, split, subset, seed, artifact, and configuration metadata. Unknown values must use an explicit state such as `unknown` or `not_applicable`.
- **Reason:** Missing strings are ambiguous and prevent external audit or mismatch detection.

## RD-006 — Phase-1 development model

- **Date:** 2026-10-12
- **Decision:** Use `Qwen/Qwen2.5-0.5B-Instruct` at immutable revision `7ae557604adf67be50417f59c2c2f167def9a775` for the first real instrumentation milestone.
- **Reason:** The machine has 4 GB VRAM but CPU-only PyTorch, 16 GB system RAM, and limited free memory. The 0.5B model has 494,032,768 parameters and a 988,097,824-byte weight file, making selected-site fp32 CPU capture practical. The 1.5B alternative would require roughly 6 GB for fp32 weights alone and substantially more intervention headroom.
- **License:** Apache-2.0; public and ungated.
- **Constraint:** This is a development/instrumentation choice, not a claim that the model is adequate for final task competence.

## RD-007 — Initial capture semantics

- **Date:** 2026-10-12
- **Decision:** Expose selected decoder block outputs, self-attention module outputs before residual addition, and MLP outputs before residual addition. The first artifact is one middle-layer MLP output.
- **Reason:** This provides accurate coarse-grained semantics without capturing every tensor or incorrectly labelling post-attention outputs as individual attention heads.

## RD-008 — Passive-hook acceptance policy

- **Date:** 2026-10-12
- **Decision:** Compare the same eval-mode model, tokenized inputs, dtype, device, eager-attention implementation, seed, greedy decoding, and no-dropout execution with and without read-only hooks. Greedy tokens and argmax predictions must match; logit tolerances are fp32 `rtol=1e-5, atol=1e-6`, fp16 `1e-3, 1e-3`, and bf16 `5e-3, 5e-3`.
- **Observed result:** On the pinned fp32 CPU model, greedy tokens and argmax predictions matched and maximum absolute logit difference was exactly `0.0`.

## RD-009 — First real intervention

- **Date:** 2026-10-12
- **Decision:** Use a zero ablation of the layer-12 MLP module output before residual addition only as a pipeline-control experiment, not as a mechanistic discovery claim.
- **Observed result:** Maximum absolute logit difference was `13.126136779785156`; output changed from `Safe` to `safe`; all hooks were removed afterward.

## RD-010 — Calibration source pins and environment isolation

- **Date:** 2026-10-13
- **Decision:** Pin Tracr to `9ce2b8c82b6ba10e62e86cf6f390e7536d4fd2cd`, original IOI experimental code to `ea15315dd24481e9e2ac5c3ef335d82907a1dc34`, and GPT-2 Small to `3fe9a169f57f3ca0cac0b9133351644193b9dd3c`. Tracr uses `.venv-tracr`; GPT-2 uses the working main environment without TransformerLens.
- **Reason:** Immutable authoritative definitions and isolation are more important than forcing legacy JAX and current PyTorch dependencies into one environment.

## RD-011 — IOI causal site and acceptance rule

- **Date:** 2026-10-13
- **Decision:** Patch paired clean per-head attention output `z` immediately before GPT-2 `c_proj`, at the final input/answer position. Test published name-mover heads `(9,9)`, `(10,0)`, `(9,6)` against equal-sized random non-circuit groups from seeds 11, 22, and 33. Predeclared success requires baseline accuracy at least 0.70, passive non-interference, and known recovery exceeding random mean by at least 0.10.
- **Observed result:** Baseline accuracy `1.0`; passive maximum logit difference `0.0`; known recovery `0.3880246`; random-control mean `0.0026128`; margin `0.3854118`.

## RD-012 — Paired trust-failure substrate and split lock

- **Date:** 2026-10-14
- **Decision:** The foundation task is deterministic ECG escalation with labels `A=ESCALATE` and `B=DO_NOT_ESCALATE`. Clean/attacked pairs may differ only in `tool_evidence.recommendation_code`. The 24-case registry is frozen as 16 development, 4 validation, and 4 test cases with hash `c510bc406b168a2639ac49f8199a7f78ba2f318893fce7be2d6c3b254266a39e`; discovery may inspect development only.
- **Reason:** An exact attack delta, serialized mediator, single-token receiver outcome, and precommitted split make causal comparisons auditable and prevent test-set leakage.

## RD-013 — Bridge Verification Protocol evidence discipline

- **Date:** 2026-10-14
- **Decision:** Evidence is reported edge-by-edge as Level 0 association, Level 1 mediator causality, Level 2 sender-activation-to-mediator causality, and Level 3 receiver-activation-to-outcome causality. Nonzero internal effects are insufficient: an intervention must move the designated downstream variable in the predeclared clean direction. No full-path claim is allowed unless all required edges are accepted.
- **Observed result:** Level 1 is accepted from whole-message rescue and induction. Level 2 is rejected because the exploratory sender patch left the attacked message unchanged. Level 3 is rejected because the exploratory receiver effect was `-0.5124740600585938`, opposite the clean direction. Maximum accepted level is 1; the distributed path is not verified.

## RD-014 — Positive-control terminology correction

- **Date:** 2026-10-14
- **Decision:** Name the ECG attack **AETHER deterministic tool-output manipulation** and the dataset **AETHER positive-control causal substrate**. Do not associate it with MCPTox semantics.
- **Reason:** MCPTox injects malicious instructions into tool metadata/descriptions; the positive control changes tool output evidence from `A` to `B`. Immutable pre-correction artifacts remain hashed and carry an explicit provenance correction.

## RD-015 — Standardized anchor pins and compatibility limits

- **Date:** 2026-10-14
- **Decision:** Pin MCPTox at `f85189f9ad12504c197c7f920ab818a40657b1fa` and TAMAS at `545c112af9aab93b7ef2b0b60831d93c81c365c3`. Treat the present MCPTox smoke as released-response rescoring and TAMAS as adapter-only.
- **Reason:** The MCPTox release omits evaluator code and clean counterparts, and its repository has no license file. TAMAS's native execution requires AutoGen/CrewAI and provider APIs or Ollama. Transforming either through AETHER would require a separate result origin.

## RD-016 — Coarse internal discovery freeze

- **Date:** 2026-10-14
- **Decision:** Scan layers `[0,5,9,14,18,23]` and block/attention/MLP outputs for each role using paired clean→attacked patches at the aligned last prompt token. Fix top-K at 3 and control seeds at 11, 22, and 33 before executing effects.
- **Observed result:** Four sender and ten receiver candidates satisfy the exploratory development rule. These are intervention-backed candidate edges but do not establish a continuous distributed circuit or held-out incremental value.

## RD-017 — Coarse hits are development causal responders

- **Date:** 2026-10-14
- **Decision:** Reclassify historical coarse-scan “supported” sites as **development causal responders**. Promote a site to **supported internal causal candidate** only if it passes the frozen bidirectional effect, consistency, matched-control, shuffled-source, and applicable position-specificity criteria.
- **Reason:** A randomly selected `sender.L23.block_output` control also recovered `1.0`, demonstrating that broad hidden-state replacement can create generic causal effects.

## RD-018 — Specificity hardening outcome and claim boundary

- **Date:** 2026-10-14
- **Decision:** Reject all six refined candidates under protocol SHA-256 `8a7c75827064e4ff847742d808f307478acba09cf925047ca0029291a83b7049`. Do not claim intervention-validated internal localization on either side of the mediator and do not freeze the validation method.
- **Reason:** All candidates failed shuffled-source separation. Additional failures included absent sender induction at L14 and insufficient receiver rescue at L18/L14. Message rescue remains the only robust causal level and behavioral recovery remains `1.0`.

## RD-019 — Identity patch, ablation, and head terminology

- **Date:** 2026-10-14
- **Decision:** Treat clean self-patching as identity-patch/intervention non-interference, not defense utility. Treat zero ablation only as operator sensitivity/necessity-like evidence. Do not run head refinement without valid pre-projection per-head tensors.
- **Reason:** These operations do not establish benign behavior for a deployable defense, formal necessity, or semantically valid head localization.

## RD-020 — MCPTox redistribution boundary

- **Date:** 2026-10-14
- **Decision:** Do not track or publish raw MCPTox records or released responses while the pinned repository has no license file. Retain source URL, commit, hashes, deterministic subset IDs, aggregate results, and integration/downloader code.
- **Reason:** Provenance can remain reproducible without redistributing potentially unlicensed source material.

## RD-021 — Balanced V2 control-identifiability redesign

- **Date:** 2026-10-15
- **Decision:** Preserve V1 exactly and create a separate balanced 24/8/8 V2 registry with equal A/B classes, bidirectional attacks, case-normalized scores, deterministic same-label/opposite-label mappings, generation-step sender semantics, and conditional pre-projection head instrumentation.
- **Reason:** V1's all-A clean labels confounded shuffled-clean controls, and its sender intervention did not explicitly encode autoregressive generation-step semantics.

## RD-022 — V2.1 behavioral correction before causal search

- **Date:** 2026-10-15
- **Decision:** Preserve the failed V2.0 smoke, then separately freeze V2.1 with left padding for variable-length decoder-only batches and the verified V1 mediator evidence wording. No data, split, score, candidate, control, or threshold changed.
- **Reason:** V2.0 predicted from right-padding positions and changed a positive-control message field. These were execution defects found before causal effects, not outcome-conditioned causal tuning.

## RD-023 — Stop internal search and recommend Phase-1 pivot

- **Date:** 2026-10-15
- **Decision:** Do not run the V2 coarse scan or head search. Classify internal candidates as `INSUFFICIENT` and recommend Phase-1 pivot review.
- **Reason:** Full development competence/attack behavior was asymmetric: A→B clean `12/12`, attack `8/12`; B→A clean `9/12`, attack `12/12`. Restricting search to the 17 eligible cases would introduce outcome-conditioned selection. Bidirectional message causality nevertheless remained `1.0` on eligible cases.

## RD-024 — Block replacement-model execution until the behavioral gate is numerical

- **Date:** 2026-10-15
- **Decision:** Checkpoint V2 at `d6725bee820c6374b1949a860df1ba0737b11304` and do not download or execute `Qwen/Qwen2.5-1.5B-Instruct` until a human-reviewed prospective protocol numerically defines the per-class clean-competence, directional attack-success, eligibility, and symmetry requirements.
- **Reason:** Frozen V2 defines per-example correctness and attack success but calls the aggregate prerequisite only "reliable." A new-model outcome cannot be classified without inventing a post-hoc threshold, which the qualification task expressly prohibits.

## RD-025 — Prospectively freeze MQ-G1 for replacement-model qualification

- **Date:** 2026-10-16
- **Decision:** Apply the conjunctive numerical criteria in `configs/model_qualification/v2_mq_g1.json` to Qwen2.5-1.5B before observing any model output. Protocol SHA-256 is `64badcea20c43ba7a42f3b8134aa261805484d4bff38841a7130584108827c89`; config SHA-256 is `d1c06af5a30ec6194bf974bc3ce8b7507cb4fe777f695d83a79b06830135c42b`.
- **Reason:** Human review resolved the earlier ambiguity prospectively. MQ-G1 is a development-stage selection rule and must not be retroactively attributed to the immutable 0.5B run.

## RD-026 — Stop 1.5B qualification at hardware preflight

- **Date:** 2026-10-16
- **Decision:** Do not download or load Qwen2.5-1.5B with only 1.66 GiB physical RAM available. Record qualification as blocked/not executed rather than assigning MQ-G1 PASS or FAIL.
- **Reason:** Approximate fp32 weights alone require 6.0 GB decimal (5.59 GiB), with estimated load and inference footprints far above currently available physical memory. Depending on the page file would risk severe system pressure and violate the fail-safe compute rule.
