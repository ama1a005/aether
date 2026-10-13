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
