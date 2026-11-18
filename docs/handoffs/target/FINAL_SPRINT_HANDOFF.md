# Member 1 — Final Sprint Handoff

**Owner:** Member 1 (m1)  
**Branch:** `m1/target-harness`  
**Base lm commit:** `4a05df1ea1ced1030fa959259dfe6434f5ae03b3`  
**Sprint documents commit:** `299dfa0b258c7c4f6732c459d98f5663fd8ecbcd` (in ancestry of HEAD)  
**Date:** 2026-11-18  

---

## 1. Owner and Branch
- **Owner:** Member 1 (`m1/target-harness`)
- **Primary Paths:** `target/`, `configs/experiments/`, `docs/handoffs/target/`
- **Reviewed Paths:** `benchmarks/run_native_official.py`, `benchmarks/nov19_bfcl/`, `experiments/phase1/qwen_agent_c.py`, `experiments/supporting_nov19/agent_c/`, `scripts/verify_demo_package.py`, `demo/frontend/`

---

## 2. Base lm Commit and Final Commits
- **Base lm commit:** `4a05df1ea1ced1030fa959259dfe6434f5ae03b3`
- **Sprint base commit:** `299dfa0b258c7c4f6732c459d98f5663fd8ecbcd`
- **Final commit:** `7f5470005e2d5ea13ae1541b48f1299a38ab8ee0`

---

## 3. Files Changed
- `scripts/verify_demo_package.py` — added deterministic root path resolution (`sys.path.insert(0, str(ROOT))`) prior to importing backend app, ensuring standalone invocability without external PYTHONPATH dependency.
- `docs/handoffs/target/FINAL_SPRINT_START.md` — baseline environment, hardware inventory, model qualification audit, BFCL readiness audit, and Agent C status.
- `docs/handoffs/target/DEMO_FINAL_RUNBOOK.md` — complete Windows and Linux startup, port mappings (8000), health verification endpoints, shutdown commands, and live review checklist.
- `docs/handoffs/target/FINAL_SPRINT_HANDOFF.md` — this formal handoff document.

---

## 4. Commands Executed
```bash
# Baseline tests and package installation
python -m pip install pyyaml torch --index-url https://download.pytorch.org/whl/cpu numpy psutil pandas fastapi httpx

# Full member-1 test suite
python -m pytest \
  tests/unit/test_target.py \
  tests/unit/test_bfcl_qwen25_adapter.py \
  tests/unit/test_native_official_package.py \
  tests/unit/test_bench_nov19_bfcl.py \
  tests/unit/test_qwen_agent_c.py \
  tests/unit/test_support_nov19_agent_c.py \
  tests/integration/test_target_pipeline.py \
  tests/integration/test_support_nov19_agent_c_integration.py \
  tests/integration/test_review_demo_e2e.py -q

# Demo frontend verification and build
cd demo/frontend
npm.cmd ci
npm.cmd test -- --run
npm.cmd run build
cd ../..

# Demo package automated verifier
python scripts/verify_demo_package.py
```

---

## 5. Exact Tests Passed / Failed / Skipped

### Python Test Suite (51 total tests):
```text
tests/unit/test_target.py ................                               [16 passed]
tests/unit/test_bfcl_qwen25_adapter.py ..                                [ 2 passed]
tests/unit/test_native_official_package.py ..                            [ 2 passed]
tests/unit/test_bench_nov19_bfcl.py ..............                       [14 passed]
tests/unit/test_qwen_agent_c.py .                                        [ 1 passed]
tests/unit/test_support_nov19_agent_c.py ........                        [ 8 passed]
tests/integration/test_target_pipeline.py ...                            [ 3 passed]
tests/integration/test_support_nov19_agent_c_integration.py ...          [ 3 passed]
tests/integration/test_review_demo_e2e.py ..                             [ 2 passed]
```
- **Passed:** 51
- **Failed:** 0
- **Skipped:** 0
- **Warnings:** 1 (`PytestUnknownMarkWarning` for custom `integration` mark in `test_support_nov19_agent_c_integration.py`)

### Frontend Vitest Suite (5 total tests):
- `src/App.test.tsx` (3 tests passed)
- `src/components/PipelineView.test.tsx` (2 tests passed)
- **Passed:** 5, **Failed:** 0, **Duration:** 5.36s

### Frontend Build:
- `npm run build` produced `dist/index.html` (170 B), `dist/assets/index-lckqjqcD.css` (3.14 kB), `dist/assets/index-BU5rljys.js` (207.81 kB)

---

## 6. External Resources and Revisions
- **BFCL Package:** `bfcl_eval==2026.3.23` (pinned wheel SHA-256: `3bb6dfa5f0c68ad403c9ec50b00db2bb3b4cc9b38ab1ff33f48fe30d853d3a0a`)
- **Qwen Model:** `Qwen/Qwen2.5-1.5B-Instruct`
- **Model Revision:** `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`
- **Tokenizer Revision:** `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`
- **Model Snapshot Manifest Hash:** `1b282b730f38fbe992608e8837fe0f619463a767f93e08d97cd0950d55644f11`

---

## 7. Artifact Paths and SHA-256
| Artifact | Path | SHA-256 |
|---|---|---|
| Sprint Start Document | `docs/handoffs/target/FINAL_SPRINT_START.md` | `53cf4057c886826ea7c7d5e9ef6f2562a4ee41bf9a96a27f2ef155aa5c5d6e42` |
| Demo Final Runbook | `docs/handoffs/target/DEMO_FINAL_RUNBOOK.md` | `cc9c45bc342cce22c0cd7f2c9ecee5d8dfcfccd922278731de46d6e31019d31b` |
| Demo Verifier Script | `scripts/verify_demo_package.py` | `a8abbf27c5f442be80e3cf9dc0418ae5694c6221bf47069764fb433b5fe6fe81` |
| Qualified Snapshot Manifest | `results/phase1/model_qualification/qwen15b_kaggle_20261110/model_snapshot_manifest.json` | `1b282b730f38fbe992608e8837fe0f619463a767f93e08d97cd0950d55644f11` |

---

## 8. Verifier Command and Full Result
Command:
```bash
python scripts/verify_demo_package.py
```
Output:
```json
{
  "overall": "PASS",
  "case_count": 12,
  "phase1_gate_count": 22,
  "frontend_build_verified": true,
  "live_external_services_tested": false,
  "claim_boundary": "Network-free packaging verification; not live MCP or model evidence."
}
```

---

## 9. Completion Gates Affected
- `target_harness_verification`: **PASS** (all 51 unit/integration tests passing; deterministic review execution verified).
- `review_demo_packaging`: **PASS** (automated static and API verifier passing; frontend built; runbook documented).
- `bfcl_official`: **BLOCKED_HARDWARE_PACKAGE** (Preflight correctly halts locally because `bfcl_eval` and CUDA GPU are absent on Windows; dry-run and verifier tested fail-closed; execution notebook pinned to `notebooks/aether_bfcl_official.ipynb`).
- `real_qwen_agent_c`: **READY_FOR_EXTERNAL_EXECUTION** (Runner audited, integration tests passing, Agent B immutability preserved; local execution blocked because Qwen model snapshot is stored on Kaggle; pinned notebook at `notebooks/aether_qwen_agent_c.ipynb`).

---

## 10. Supported Claims and Non-Claims

### Supported Claims:
1. Target harness, two-agent protocol, and three-agent pipeline correctly serialize schemas, preserve RNG determinism, and uphold contracts without hidden fallbacks.
2. In three-agent pipeline, Agent B's raw decision is immutable and stored separately from Agent C's review.
3. Review demo is locally launchable, serves production assets from `demo/frontend/dist` on port 8000 without a secondary proxy, verifies 12 cases, and exhibits expected attack-induced flip and causal rescue recovery.
4. BFCL and Agent C runners fail closed, reject dirty git state, disallow protected-split execution, and maintain required denominators.

### Explicit Non-Claims:
1. BFCL official evaluation was **NOT** executed locally (requires Linux GPU environment with `bfcl_eval` and vLLM).
2. Agent C was **NOT** executed with live Qwen weights locally (weights reside in Kaggle storage).
3. The demo's model-free deterministic path does **NOT** constitute real-model mechanistic evidence.

---

## 11. Remaining Blockers
- **BFCL Execution:** Requires running `notebooks/aether_bfcl_official.ipynb` in a Linux CUDA GPU environment with `bfcl_eval` installed.
- **Agent C Execution:** Requires running `notebooks/aether_qwen_agent_c.ipynb` in a Kaggle environment where the qualified model snapshot is mounted.

---

## 12. Manual Integration Steps
1. Checkout `m1/target-harness` into the review workspace.
2. Confirm diff touches only `scripts/verify_demo_package.py` and `docs/handoffs/target/`.
3. Verify all 51 Python tests pass:
   ```bash
   python -m pytest tests/unit/test_target.py tests/unit/test_bfcl_qwen25_adapter.py tests/unit/test_native_official_package.py tests/unit/test_bench_nov19_bfcl.py tests/unit/test_qwen_agent_c.py tests/unit/test_support_nov19_agent_c.py tests/integration/test_target_pipeline.py tests/integration/test_support_nov19_agent_c_integration.py tests/integration/test_review_demo_e2e.py -q
   ```
4. Verify demo package:
   ```bash
   python scripts/verify_demo_package.py
   ```
5. Merge `m1/target-harness` into `lm`.
