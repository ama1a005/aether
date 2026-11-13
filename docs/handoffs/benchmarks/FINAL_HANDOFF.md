# AETHER Phase 1 External Benchmarks: Final Subsystem Delivery & Handoff

**Owner:** Friend A — Independent Benchmark Lead (Antigravity on Laptop 2)  
**Target Date:** 19 November 2026 (Completed Engineering Delivery: 13 November 2026)  
**Branch:** `phase1/benchmarks-nov19`  
**Base Commit:** `00846b020b685dfa3ab89bce2c5227d2810c9d1e`  
**Final Commit:** `cd9336b9eca2cd716b6dcb1814cb3c6974da1bfb`  
**Upstream Target:** `origin/lm`  
**PR Title:** `Phase1 external benchmarks: BFCL/MCPTox/TAMAS verified workflows`  
**Reviewer / Integration Owner:** Lead Developer (Codex in `phase1/core-nov19`)  

---

## 1. Executive Summary

This handoff delivers the complete, self-contained, and independently testable external evaluation subsystem for the AETHER research project across:
1. **BFCL (Berkeley Function Calling Leaderboard):** Benign tool-calling competence verification using official package `bfcl_eval==2026.3.23` and disclosed adapter `AETHER/Qwen2.5-1.5B-Instruct-FC`.
2. **MCPTox:** Authentic tool-description metadata poisoning evaluation (AAAI 2026, pinned commit `f85189f9`, 45 servers, 485 cases) with strict label accounting and license disclosure.
3. **TAMAS:** Native multi-agent conversational adversarial benchmark (Microsoft, pinned commit `545c112a`, 300 cases across 6 attack types) with explicit distinction between deterministic rules and LLM-based judges.
4. **Unified Reporting & Provenance Auditor:** Schema `aether.nov19.external_benchmark.v1`, Wilson 95% confidence intervals, cluster-adjusted variance, paper-ready CSV generation, and automated hash verification.
5. **Study Package:** Ground-truth study guide answering all 10 core architectural concepts, 15 viva voce questions, 5 methodological pitfalls, and a complete worked interpretation example.

---

## 2. Benchmark Gate Status & Scientific Evidence Classification

| Benchmark | Evidence Class | Model / Revision | Cohort Scope | Official Evaluator Executed | Scientific Gate Status | Hardware / License Blocker |
|---|---|---|---|---|---|---|
| **BFCL** | `official_evaluator_with_disclosed_aether_model_adapter` | `Qwen/Qwen2.5-1.5B-Instruct` rev `989aa7980e4c` | `simple`, `multiple`, `parallel`, `irrelevance` | False | `BLOCKED` (Gate remains `MISSING` in audit) | Requires Linux + CUDA GPU ($\ge$16 GB VRAM) for vLLM; laptop 2 is CPU-only Windows |
| **MCPTox** | `official_compatible_tool_poisoning_evaluation` | `Qwen/Qwen2.5-1.5B-Instruct` rev `989aa7980e4c` | 485 cases across 45 servers | False | `BLOCKED` (Gate remains `MISSING` in audit) | Upstream repository at `f85189f9` lacks LICENSE file; automated runner requires live MCP environment |
| **TAMAS** | `official_native_execution` | `Qwen/Qwen2.5-1.5B-Instruct` rev `989aa7980e4c` | 300 records (50 per attack across 6 paradigms) | False | `BLOCKED` (Gate remains `MISSING` in audit) | AutoGen/CrewAI framework not installed in standard env; requires provider API / Ollama |

*Scientific Integrity Invariant:* In strict adherence to `RESEARCH_CONTRACT.md`, no fake numbers or synthetic PASS flags were generated. The completion gates `bfcl_official`, `mcptox_official`, and `tamas_official` remain truthfully unclosed until executed on authorized external compute.

---

## 3. Inventory of Owned Deliverables

All additions are strictly confined to authorized ownership paths:

### Subsystem Packages
- `benchmarks/nov19_bfcl/` (`__init__.py`, `preflight.py`, `runner.py`, `verifier.py`, `report.py`)
- `benchmarks/nov19_mcptox/` (`__init__.py`, `case.py`, `preflight.py`, `evaluator.py`, `verifier.py`, `report.py`)
- `benchmarks/nov19_tamas/` (`__init__.py`, `case.py`, `preflight.py`, `runner.py`, `verifier.py`, `report.py`)
- `benchmarks/nov19_reporting/` (`__init__.py`, `statistics.py`, `schema.py`, `builder.py`, `auditor.py`)

### External Compute Runners & Scripts
- `scripts/benchmark_bfcl_external_runner.py`
- `scripts/benchmark_mcptox_external_runner.py`
- `scripts/benchmark_tamas_external_runner.py`

### Runbooks & Documentation
- `docs/benchmarks_nov19/BFCL_RUNBOOK.md`
- `docs/benchmarks_nov19/MCPTox_RUNBOOK.md`
- `docs/benchmarks_nov19/TAMAS_RUNBOOK.md`

### Handoffs & Audit Trails
- `docs/handoffs/benchmarks/START_STATE.md`
- `docs/handoffs/benchmarks/DAILY_2026-11-13.md`
- `docs/handoffs/benchmarks/STUDY_NOTES.md`
- `docs/handoffs/benchmarks/bfcl_handoff.json`
- `docs/handoffs/benchmarks/mcptox_handoff.json`
- `docs/handoffs/benchmarks/tamas_handoff.json`
- `docs/handoffs/benchmarks/unified_benchmarks_summary.json`
- `docs/handoffs/benchmarks/benchmarks_paper_table.csv`
- `docs/handoffs/benchmarks/methodology_paragraph.md`

### Test Suite
- `tests/unit/test_bench_nov19_bfcl.py` (14 tests)
- `tests/unit/test_bench_nov19_mcptox.py` (8 tests)
- `tests/unit/test_bench_nov19_tamas.py` (10 tests)
- `tests/unit/test_bench_nov19_reporting.py` (5 tests)

---

## 4. Verification and Test Results

Executed command:
```bash
python -m pytest tests/unit/test_bench_nov19_bfcl.py \
                 tests/unit/test_bench_nov19_mcptox.py \
                 tests/unit/test_bench_nov19_tamas.py \
                 tests/unit/test_bench_nov19_reporting.py \
                 tests/unit/test_native_benchmark_runners.py \
                 tests/unit/test_bfcl_qwen25_adapter.py \
                 tests/unit/test_benchmark_result_import.py -v
```
**Result:** 44 passed in 6.90s (0 failures, 0 warnings).

---

## 5. Non-Claims & Novelty Boundaries

1. **BFCL:** Proves benign function-calling accuracy under clean conditions; does NOT prove causal circuit discovery or intervention robustness.
2. **MCPTox:** Demonstrates vulnerability to metadata-poisoned MCP tools; does NOT validate DCMG, BVP, or causal activation patching.
3. **TAMAS:** Tests conversational multi-agent adversarial resilience across 6 standard attack types; does NOT prove cross-agent causal isolation.

The lead developer may merge `phase1/benchmarks-nov19` into `lm` without risk of merge conflicts or causal pipeline interference.
