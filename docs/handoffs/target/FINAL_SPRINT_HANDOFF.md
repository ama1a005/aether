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
- **Final commit:** `a41296b34ea6cf76503c4f74d081f95fecfc5ca6`

---

## 3. Files Changed
- `scripts/verify_demo_package.py` — added deterministic root path resolution (`sys.path.insert(0, str(ROOT))`) prior to importing backend app, ensuring standalone invocability without external PYTHONPATH dependency.
- `demo/mcp_server/server.py` — added dual `FastMCP` / `MCPServer` compatibility import for official MCP SDK versions 1.x and 2.x stdio transport.
- `tests/integration/test_demo_mcp_stdio.py` — updated attribute access to support both camelCase and snake_case attributes across MCP SDK releases, ensuring full stdio tool discovery and execution tests pass.
- `scripts/build_kaggle_official_benchmark_notebook.py` & `scripts/build_kaggle_supporting_notebook.py` — updated clone target from deprecated `phase1/core-nov19` to active `lm` branch.
- `notebooks/aether_bfcl_official.ipynb` & `notebooks/aether_qwen_agent_c.ipynb` — regenerated Kaggle notebooks with `lm` branch clone and pinned commits.
- `pyproject.toml` — registered `integration` pytest marker to ensure zero test warnings.
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
  tests/integration/test_demo_mcp_stdio.py \
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

### Python Test Suite (52 total tests):
```text
tests/unit/test_target.py ................                               [16 passed]
tests/unit/test_bfcl_qwen25_adapter.py ..                                [ 2 passed]
tests/unit/test_native_official_package.py ..                            [ 2 passed]
tests/unit/test_bench_nov19_bfcl.py ..............                       [14 passed]
tests/unit/test_qwen_agent_c.py .                                        [ 1 passed]
tests/unit/test_support_nov19_agent_c.py ........                        [ 8 passed]
tests/integration/test_target_pipeline.py ...                            [ 3 passed]
tests/integration/test_support_nov19_agent_c_integration.py ...          [ 3 passed]
tests/integration/test_demo_mcp_stdio.py .                               [ 1 passed]
tests/integration/test_review_demo_e2e.py ..                             [ 2 passed]
```
- **Passed:** 52
- **Failed:** 0
- **Skipped:** 0
- **Warnings:** 0

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

---

## Supplemental follow-up — 2026-11-18

The final-sprint audit found two launch/error-reporting defects and corrected
them without touching the pre-existing CORE-04 or evidence-related working-tree
changes:

- `BFCLRunner.plan()` now propagates native-plan construction errors instead
  of silently replacing them with `native_plan: null`.
- `scripts/benchmark_bfcl_external_runner.py` now adds the repository root to
  `sys.path`, so the runbook's direct `python scripts/... --dry-run` command
  works from a clean checkout.

### Verification performed

- BFCL and native-package model-free tests: **18 passed** after these changes.
- Full Member 1 Python suite: **61 passed, 2 skipped**. The two review-demo
  end-to-end cases are skipped by their declared environment gate.
- BFCL dry-run starts and creates the pinned native plan, then correctly
  refuses execution because `bfcl_eval==2026.3.23`, CUDA, and the model snapshot
  are unavailable on this Windows host. No official score or result bundle was
  created.
- Demo package verifier: **PASS**, 12 demo cases and 22 Phase-1 gates; this is
  network-free packaging evidence only.
- Frontend: five Vitest tests passed and the production build succeeded.
- MCP stdio: the integration test passed when run with permission to create
  its Windows child-process pipe.
- Real-Qwen Agent C: its SUPPORT-02 config dry-run passes. No model execution
  was started; the qualified snapshot is remote and the canonical protocol
  proposal remains at human review. Supporting Agent-C evidence is not part of
  the causal core.

The follow-up implementation and regression tests are in commit
`4b972a85c287ea8e0726bd775141d635fd349e03` on `m1/target-harness`.

### Follow-up limitations

BFCL and real-Qwen Agent C still require their reviewed, commit-pinned Linux /
Kaggle execution paths. The demo's external MCP service behavior was not tested
live. No evidence gate is promoted by these software checks.


## Final requirements audit ? 2026-11-19

Commits pushed to `origin/m1/target-harness`:
- `e0d084bf7f5348a134c4e3a9c6851aec728df096` ? target, BFCL, Agent C, demo verifier and regression fixes.
- `2ffcbbc0639cca869ff9446fafbb2444cd1769d5` ? regenerated BFCL and Agent C external notebooks pinned to the source commit above.

The audit tightened the target runner to require its declared attack spec and write unique run-scoped traces with provenance; hardened the canonical BFCL runner with exact config/pin validation, wheel and full model/tokenizer snapshot checks, native raw-output re-verification, error denominators and bundle inventory; added an independent BFCL bundle verifier; corrected Agent C to use the paired development cohort, retain source inputs, checkpoint each case-condition atomically and support hash-checked resume; added an Agent C bundle verifier; extended the demo verifier to exercise the unavailable external-MCP 503 path without fallback; and updated the BFCL runbook.

### Current execution blockers

- **BFCL:** No approved protocol decision currently exists at `results/phase1/protocol_approvals/bfcl_official.json`. The canonical runner and Kaggle notebook now require a human decision bound to the exact frozen config before model download/access. This Windows host also lacks the pinned BFCL wheel, CUDA/vLLM and the local Qwen snapshot. The notebook verifies all prerequisites and exports raw outputs, hashes and an archive for atomic ingestion after execution. No BFCL score was generated.
- **Agent C:** `results/phase1/protocol_approvals/agent_c_qwen_development.json` remains absent. The canonical runner fails before loading the retained Qwen trace or model data until approval. No Agent C bundle was generated. The clean commit-pinned notebook and paired, checkpointable execution/verifier path are ready after approval.
- **Demo:** Automated package check passes (12 fixtures, 22 evidence stages, clean/attack distinction and explicit external MCP failure). MCP stdio integration passes. The actual Docker WSO2 stack was not started or manually reviewed live on this host.

### Verification in this audit

- Member 1 focused unit set: **52 passed**.
- Member 1 integration set, including target pipelines, three-agent pipeline and MCP stdio: **8 passed**.
- `python -m scripts.verify_demo_package`: **PASS**, frontend production assets verified; external MCP outage explicitly returns 503 without fallback.
- Full `tests/unit/`: **606 passed, 1 failed**. The unrelated existing completion-audit test fails because QCI-2 verification finds duplicate `dependency-check.log` artifacts (`cannot uniquely resolve artifact`). Its QCI/evidence files were not modified by this Member 1 change.
- Notebook builder tests after regeneration: **3 passed**.
- No external scientific execution was performed. Software/fixture checks are not experimental results.

The original uncommitted CORE/evidence work and untracked `reference_docs/` were left unstaged and preserved.


### Approval-gate and notebook pin follow-up ? 2026-11-19

Final source commit: `e8966b4ed6dd4cdd354322666ceaef3364b576d0` adds a mandatory BFCL approval JSON gate bound to the exact canonical config. The notebook checks approval before model download; a missing decision leaves the path blocked. Commit `16c43d37cd87ccffd6a0f9c38392406461a8ffaf` repins both external notebooks to that exact source commit. Both commits are pushed to `origin/m1/target-harness`.

Regression verification after the approval change: **26 relevant unit tests passed**, then **7 approval/notebook tests passed**; the demo verifier passed. The full unit-suite result remains 606 passed and the one unrelated QCI-2 artifact-resolution failure documented above. No unapproved BFCL or Agent-C run was started.


## Local/external execution feasibility guide ? 2026-11-19

The beginner execution guide is `docs/handoffs/target/EXTERNAL_EXECUTION_GUIDE.md`. It corrects an earlier overstatement in this handoff: the canonical Agent-C task does **not** load a Qwen model. It replays the 24 retained real-Qwen A/B development traces through frozen deterministic Agent C for 48 paired conditions, so local Windows CPU execution is appropriate after human approval. The Qwen model remains pinned as upstream trace provenance; no weights are required for this review.

BFCL remains Linux/CUDA external-only. Its preflight now checks that vLLM is installed and rejects NVIDIA devices below compute capability 7.5 as well as devices below the frozen 16-GiB memory floor. This guards against a Kaggle P100 that has 16 GiB but is incompatible with current vLLM CUDA wheels. The BFCL notebook installs the vLLM backend and supports Kaggle or a compatible Linux Jupyter Pod.

No approval was created and no scientific experiment was started during this preparation. Local preflight on the current Windows machine correctly reports missing `bfcl_eval`, missing vLLM, no CUDA device, and the absent local Qwen snapshot.


### Beginner execution materials and final source pins ? 2026-11-19

- Preparation commit `d8adc6cd4c21062c0dec505b3cbadc8a0f317460` adds the measured feasibility analysis, human approval checklist, BFCL backend/compute-capability preflight, Agent-C source-Qwen provenance, and fixes the Agent-C CLI's completed-output return path.
- Commit `c31eb63662175ad343cf1d89301e9a39754ea7a1` keeps execution environments outside clean source checkouts and removes unnecessary editable installs that could make them dirty.
- Commit `97fe389273c2ac91154ee6dc0df1bc922a3d8cae` regenerates both notebooks against that exact source commit. All three are pushed to `origin/m1/target-harness`.
- Relevant model-free tests after these updates: **30 passed**, followed by **3 notebook builder tests passed**. Both notebook builders compile every code cell. No approval was created and no scientific run was started.

The BFCL notebook installs vLLM, checks its presence, CUDA, 16-GiB VRAM and compute capability 7.5 before model download. Kaggle is conditional on actually offering a compatible GPU; a Linux Pod with an explicitly selected compatible card is the reliable option. The Agent-C procedure uses a clean clone and an environment outside it, because the evidence manifest requires a clean Git source. Its currently frozen Agent-C policy is deterministic; the retained real-Qwen part is the upstream A/B trace.
