# BENCH-00: Code Audit and Frozen Source Inventory (START_STATE)

**Timestamp:** 2026-11-13T20:45:00+05:30  
**Owner:** Friend A (External Benchmark Lead, Antigravity on laptop 2)  
**Branch:** `phase1/benchmarks-nov19`  
**Base Commit:** `00846b020b685dfa3ab89bce2c5227d2810c9d1e`  
**Current HEAD:** `00846b020b685dfa3ab89bce2c5227d2810c9d1e`  
**Python Environment:** 3.11.9 (Windows Store / project venv `.venv`)  
**Hardware Profile:** Windows x64, CPU-only (`torch.cuda.is_available() == False`, `Device count: 0`), RAM: 16 GB  

---

## 1. Baseline Completion Audit & Status Verification

Execution of `scripts/audit_phase1_completion.py` on the clean base commit `00846b020b685dfa3ab89bce2c5227d2810c9d1e`:
- **Overall Status:** `INCOMPLETE`
- **Total Gates:** 22
- **Status Counts:**
  - `PASS`: 6 (`qwen_qualification`, `qwen_instrumentation_acceptance`, `qwen_development_capture`, `qci_discovery_interventions`, `tracr_known_structure_intervention`, `ioi_causal_calibration`)
  - `NOT_APPLICABLE`: 1 (`qci_development_audit` - verified discovery found no supported internal candidate)
  - `INVALID`: 1 (`qci2_semantic_discovery` - ValueError: cannot uniquely resolve artifact: dependency-check.log)
  - `BLOCKED`: 1 (`qci2_semantic_development_audit` - dependency not passed)
  - `MISSING`: 13 (including `bfcl_official`, `mcptox_official`, `tamas_official`, `method_freeze_review`, `matched_search_baselines`, `mechanism_guided_remediation`, `locked_validation`, `once_only_test`, `trained_sae_qwen_evaluation`, `real_qwen_red_team`, `real_qwen_agent_c`, `second_model_qualification`, `final_verified_report`)

---

## 2. Existing Benchmark Code Path Inventory

| Code Path | Primary Input | Expected Output | Current Evidence Class | Missing Dependencies / Blockers | Officialness Boundary & Issues | Next Action |
|---|---|---|---|---|---|---|
| `benchmarks/native_runners.py` (`bfcl_plan`) | `package_version`, `model`, `categories`, `output_dir` | `NativeBenchmarkPlan` for `bfcl_eval generate` & `bfcl_eval evaluate` | Planning helper / unit tested | `bfcl_eval==2026.3.23` not installed in standard env | Plan uses official CLI, but lacks adapter registration unless using `bfcl_qwen25_plan` | Integrate into `nov19_bfcl` runner with preflight validation |
| `benchmarks/native_runners.py` (`bfcl_qwen25_plan`) | `package_version`, `model_revision`, `snapshot_manifest`, `categories`, `output_dir`, `backend` | `NativeBenchmarkPlan` invoking `benchmarks.bfcl_qwen25` | Planning helper / unit tested | Requires `vllm`/`sglang` and CUDA GPU (absent on laptop 2) | Disclosed custom adapter `AETHER/Qwen2.5-1.5B-Instruct-FC`; not unmodified leaderboard entry | Add preflight check, self-contained external compute runner |
| `benchmarks/bfcl_qwen25.py` | CLI args with `--model-revision`, `--snapshot-manifest` | In-process registration in `MODEL_CONFIG_MAPPING` and delegation to `bfcl_eval` CLI | Model adapter wrapper | Local model snapshot directory matching revision `989aa7980e4cf806f80c7fef2b1adb7bc71aa306` absent on laptop 2 | Custom registration must be explicitly disclosed; must fail if model files don't match manifest | Build independent verifier and model-free test suite |
| `benchmarks/mcptox.py` | `pure_tool.json` from pinned commit `f85189f9` | `MCPToxCase` dataclass list, label accounting | Data loader / label summarizer | No live MCP server runtime or model evaluation loop in current module | Pinned upstream has released labels, no executable runner | Build native typed case adapter, preflight validator, and official-compatible runner |
| `benchmarks/run_mcptox_smoke.py` | `.cache/benchmarks/MCPTox-Benchmark` (`pure_tool.json`, `response_all.json`) | `results/phase1/mcptox/smoke/summary.json` & `manifest.json` | Released-response smoke (rescoring Qwen3-8b labels) | Unlicensed upstream dataset requires human license determination; cache not present | Rescores published outputs; NOT a fresh Qwen2.5 evaluation | Keep strictly in `smoke/`; do not promote to `official/` |
| `benchmarks/tamas.py` | `.cache/benchmarks/TAMAS/data` (300 cases across 6 attack types) | `TAMASCase` dataclass list | Data loader | Native AutoGen/CrewAI framework and provider API credentials/Ollama | Evaluates dataset format only; no agent interaction executed | Build standalone runner with framework checks and judge distinction |
| `benchmarks/run_tamas_adapter_smoke.py` | `.cache/benchmarks/TAMAS/data` | `results/phase1/tamas/smoke/summary.json` & `adapter_rows.json` | Adapter data smoke | Local cache not cloned in clean repo | Parses cases; explicitly states `native_execution_status: not_run` | Maintain in `smoke/`; build native execution harness |
| `benchmarks/result_import.py` | Official JSON results file | Validated `BenchmarkResult` rows and aggregate summary | Evaluator import utility | None | Retains error rows in total denominator; prevents denominator loss | Reuse in reporting and verification modules |

---

## 3. Discrepancy & Registry Audit

1. **BFCL Registry vs Config:**
   - `benchmarks/REGISTRY.yaml` lists version as `pinned_release_TBD`, commit `TBD`, local_hash `TBD`.
   - `configs/benchmarks/phase1_external.yaml` pins `bfcl_eval==2026.3.23` and wheel SHA256 `3bb6dfa5f0c68ad403c9ec50b00db2bb3b4cc9b38ab1ff33f48fe30d853d3a0a`.
   - Action: Document registry synchronization requirements in handoff without editing frozen files.

2. **MCPTox Case Counts:**
   - arXiv abstract states 1,312 instances; AAAI 2026 publication states 1,348 instances.
   - Pinned git release (`f85189f9ad12504c197c7f920ab818a40657b1fa`) contains exactly 45 server groups and 485 poisoned-tool records (Template-1: 77, Template-2: 183, Template-3: 225).
   - Action: Lock denominator to 485 for the pinned release; never conflate with published numbers.

3. **TAMAS Composition:**
   - Pinned git commit `545c112af9aab93b7ef2b0b60831d93c81c365c3`.
   - Exactly 300 instances: 50 each for Byzantine, Colluding, Contradicting, DPI, Impersonation, and IPI.
   - Licenses: MIT for code, CDLA-Permissive-2.0 for data.

4. **Primary Model Snapshot:**
   - ID: `Qwen/Qwen2.5-1.5B-Instruct`
   - Revision: `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`
   - Pinned snapshot manifest in `results/phase1/model_qualification/qwen15b_kaggle_20261110/model_snapshot_manifest.json` specifies 10 exact files with SHA-256 digests.

---

## 4. Hardware and Execution Feasibility on Laptop 2

- **CUDA/GPU:** Unavailable (`torch.cuda.is_available() == False`).
- **BFCL Inference:** Official vLLM backend requires Linux and CUDA GPU. Infeasible to execute natively on this Windows laptop.
- **TAMAS Multi-Agent Execution:** Native AutoGen/CrewAI with local Ollama or LLM API keys requires external API access/keys or Ollama running with sufficient VRAM/RAM.
- **Protocol Discipline:**
  - Build robust, isolated native integration modules and strict fail-closed preflights.
  - Deliver self-contained external compute runbooks and scripts for qualified GPU environments (e.g. Kaggle / Slurm).
  - Gating status for `bfcl_official`, `mcptox_official`, and `tamas_official` will remain truthfully marked as `BLOCKED` (or `MISSING` in the gate audit) rather than fabricated.
