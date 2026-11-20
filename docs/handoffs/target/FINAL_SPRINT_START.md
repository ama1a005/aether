# Member 1 — Final Sprint Start Handoff

**Owner:** Member 1 (m1)
**Branch:** `m1/target-harness`
**Base lm commit:** `4a05df1ea1ced1030fa959259dfe6434f5ae03b3`
**Sprint documents commit:** `299dfa0b258c7c4f6732c459d98f5663fd8ecbcd` (ancestor of HEAD ✓)
**Start UTC timestamp:** 2026-11-18T12:43:00Z

---

## Environment

| Field | Value |
|---|---|
| OS | Windows-10-10.0.26200-SP0 |
| Python | 3.11.9 (CPython, MSC v.1938 64-bit AMD64) |
| pytest | 9.2.0 |
| PyYAML | 6.0.3 (freshly installed; was absent) |
| torch | NOT INSTALLED — CPU-only wheel installing in background |
| bfcl_eval | NOT INSTALLED (not available locally; requires Linux/Kaggle GPU) |
| CUDA | NOT AVAILABLE on local machine |

---

## Baseline Test Results (Step 1)

Executed:
```
python -m pytest \
  tests/unit/test_target.py \
  tests/unit/test_bfcl_qwen25_adapter.py \
  tests/unit/test_native_official_package.py \
  tests/unit/test_support_nov19_agent_c.py \
  tests/unit/test_qwen_agent_c.py \
  tests/integration/test_target_pipeline.py \
  tests/integration/test_support_nov19_agent_c_integration.py \
  -q --tb=short
```

**Result: 35 passed, 0 failed, 1 warning (PytestUnknownMarkWarning for `integration` mark)**

> NOTE: `test_bench_nov19_bfcl.py` requires `torch` (installing); will re-run when available.

---

## Qualified Model

| Field | Value |
|---|---|
| Model ID | `Qwen/Qwen2.5-1.5B-Instruct` |
| Model Revision | `989aa7980e4cf806f80c7fef2b1adb7bc71aa306` |
| Tokenizer Revision | `989aa7980e4cf806f80c7fef2b1adb7bc71aa306` |
| Qualification Result | `QUALIFIED_FOR_SEPARATE_INSTRUMENTATION_REVIEW` |
| MQ-G1 | PASS (all 12 predicates) |
| MQ-G2 | PASS (all 7 predicates) |
| MQ run timestamp | 2026-11-10T18:47:53Z |
| Model snapshot manifest SHA-256 | `1b282b730f38fbe992608e8837fe0f619463a767f93e08d97cd0950d55644f11` |
| Local snapshot path | **ABSENT** — Kaggle remote path only (`/tmp/aether-qwen-qualification/hf-cache/...`) |

---

## BFCL Readiness Audit (Step 2)

| Check | Status | Detail |
|---|---|---|
| Pinned package version | ✓ Pinned | `bfcl_eval==2026.3.23` in preflight.py and phase1_external.yaml |
| Wheel SHA-256 | ✓ Pinned | `3bb6dfa5f0c68ad403c9ec50b00db2bb3b4cc9b38ab1ff33f48fe30d853d3a0a` |
| Package installed locally | ✗ BLOCKED | `bfcl_eval` not installed — requires Linux + CUDA/vLLM (Kaggle GPU) |
| Model revision pinned | ✓ Pinned | `989aa7980e4cf806f80c7fef2b1adb7bc71aa306` |
| Snapshot manifest path | ✓ Exists in results | `results/phase1/model_qualification/qwen15b_kaggle_20261110/model_snapshot_manifest.json` |
| Local model snapshot files | ✗ BLOCKED | Snapshot path is a Kaggle remote path; model not cached locally |
| Categories frozen | ✓ Pinned | `[simple, multiple, parallel, irrelevance]` in both preflight.py and config |
| Adapter disclosure | ✓ Disclosed | `evidence_class: official_evaluator_with_disclosed_aether_model_adapter` |
| Claim label | ✓ Correct | "official evaluator with disclosed AETHER adapter" — not "unmodified leaderboard" |
| Dirty-source gate | ✓ Implemented | `run_native_official.py` checks `git status --porcelain` and raises on dirty |
| Config schema check | ✓ Implemented | Requires `schema_version: 1` and `split: development` |
| Independent verifier | ✓ Exists | `benchmarks/nov19_bfcl/verifier.py` — `BFCLArtifactVerifier` |
| Report assembler | ✓ Exists | `benchmarks/nov19_bfcl/report.py` — fail-closed, distinguishes PASS/BLOCKED/FAIL |
| Backend requirement | ✗ BLOCKED | Requires vLLM/sGLang with CUDA GPU; local machine has no CUDA |

**BFCL EXECUTION BLOCKER:** `bfcl_eval` package and CUDA GPU require a Linux GPU environment.
Execution must proceed via Kaggle or equivalent GPU notebook pinned to reviewed commit.
Notebook: `notebooks/aether_bfcl_official.ipynb`

---

## Agent C Audit (Step 3)

| Check | Status | Detail |
|---|---|---|
| Canonical entry | ✓ | `experiments/phase1/qwen_agent_c.py` |
| Prior helper | ✓ | `experiments/supporting_nov19/agent_c/runner.py` — audited, reconciled |
| Config exists | ✓ | `configs/experiments/agent_c_qwen_development.yaml` — status: `awaiting_human_protocol_review` |
| Agent B raw decision | ✓ | Stored separately in `ThreeAgentResult.agent_b_decision` — test verifies immutability |
| Agent C labeled supporting | ✓ | config `claim_boundary` explicitly says "not a third Qwen agent" |
| Development-only split | ✓ | Config enforces `split: development`, `validation_executions: 0`, `test_executions: 0` |
| Real Qwen rows available | ✓ | `results/phase1/model_qualification/qwen15b_kaggle_20261110/mq_g1_rows.json` |
| Local model for Agent C | ✗ BLOCKED | Qwen model not cached locally; config references `awaiting_human_protocol_review` |

---

## Missing Credentials / Resources

| Resource | Status |
|---|---|
| Local CUDA GPU | ABSENT |
| Local Qwen model snapshot | ABSENT (Kaggle path only) |
| `bfcl_eval` package | NOT INSTALLED (needs Linux/Kaggle) |
| `torch` package | INSTALLING (CPU-only wheel) |
| Kaggle API credentials | Not checked on local machine |

---

## Computation Notes

- Local execution environment: Windows 10, Python 3.11, no GPU
- BFCL and real-Qwen Agent C require the Kaggle GPU notebook path
- All model-independent tests pass (35/35)
- torch (CPU) installing to unblock `test_bench_nov19_bfcl.py`

---

## Next Steps

1. Wait for torch install → run `test_bench_nov19_bfcl.py`
2. Conduct demo package verification (model-free)
3. Document BFCL external blocker formally in the verifier
4. Document Agent C external blocker (model not local)
5. Write `DEMO_FINAL_RUNBOOK.md`
6. Commit all documentation to `m1/target-harness` and push
