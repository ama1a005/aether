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
