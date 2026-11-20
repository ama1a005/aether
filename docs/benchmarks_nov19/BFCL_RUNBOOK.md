# BFCL Official Evaluation Runbook (AETHER Phase 1)

**Benchmark:** Berkeley Function Calling Leaderboard (BFCL)  
**Package:** `bfcl_eval==2026.3.23`  
**Package Wheel SHA-256:** `3bb6dfa5f0c68ad403c9ec50b00db2bb3b4cc9b38ab1ff33f48fe30d853d3a0a`  
**Target Model:** `Qwen/Qwen2.5-1.5B-Instruct`  
**Model Snapshot Revision:** `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`  
**Disclosed Custom Adapter:** `AETHER/Qwen2.5-1.5B-Instruct-FC`  
**Protocol Label:** `official_evaluator_with_disclosed_aether_model_adapter`  
**Configured Categories:** `simple`, `multiple`, `parallel`, `irrelevance` (complete evaluation of this prespecified four-category subset only; not the full BFCL category suite or a leaderboard result)
**Target Output Directory:** `/kaggle/working/aether-bfcl-official-<attempt>/` (outside the source checkout)
**Inference stack:** `vllm==0.34.0`, `torch==2.14.0`, CUDA 13.0

---

## 1. Scientific Role & Novelty Boundary

BFCL measures benign tool-use / function-calling competence.  
In AETHER:
- Upstream sender agent derives decisions from tool outputs.
- A failure to call tools correctly in clean scenarios would confound tool-poisoning attacks (an apparent attack success could simply be incompetence).
- BFCL establishes baseline benign function-calling accuracy on its standard
  evaluation data. This AETHER protocol evaluates all examples in four
  prespecified BFCL categories only; it does not evaluate the full BFCL category
  suite and does not produce a leaderboard result. BFCL's own evaluation/test
  examples may be included. The config's `split: development` identifies the
  AETHER project scope: no AETHER validation or test split is accessed.
- **Novelty boundary:** Running BFCL does NOT demonstrate DCMG causality, cross-agent circuit discovery, or remediation. It provides necessary external grounding.
- **Disclosed Adapter:** Because official `bfcl_eval` 2026.3.23 does not have a native Qwen2.5 configuration out-of-the-box, we register the custom adapter `AETHER/Qwen2.5-1.5B-Instruct-FC`. This is openly labeled in all paper-facing summaries and artifacts as a disclosed model adapter, NOT an unmodified leaderboard submission.

---

## 2. Hardware and Environment Requirements

- **OS:** Linux (Ubuntu 22.04+ recommended; Windows is incompatible with vLLM)
- **Python:** 3.11
- **Accelerator:** NVIDIA GPU exposing at least 15.0 decimal GB usable VRAM and CUDA compute capability 7.5 or newer (e.g. T4, A10, L4, A100, RTX 4090). The usable floor accounts for memory reserved by Kaggle/driver runtime on a nominal 16 GB T4; Kaggle P100 (compute capability 6.0) remains rejected.
- **Driver/runtime:** CUDA 13.0 compatible environment. If runtime initialization fails or reports a different CUDA runtime, stop; do not substitute a CPU backend.
- **Inference Engine:** `vllm==0.34.0` with `torch==2.14.0` and CUDA 13.0. This compatibility overlay is in `requirements-bfcl-vllm.txt`; it deliberately supersedes the project lock's Torch patch version only in the isolated BFCL environment.
- **Dependencies:**
  ```bash
  python -m pip install -r requirements-lock.txt
  python -m pip install "bfcl_eval==2026.3.23"  # verify the recorded wheel SHA-256
  uv pip install --python .venv/bin/python -r requirements-bfcl-vllm.txt --torch-backend cu130
  ```

### Local Laptop Status (Laptop 2)
- Operating System: Windows 11
- Accelerator: CPU only (`torch.cuda.is_available() == False`, 0 GPUs)
- Status: **BLOCKED LOCALLY DUE TO HARDWARE CONSTRAINTS**.
- Gating Rule: The gate `bfcl_official` remains `MISSING` on this local machine. No synthetic or placeholder PASS file is generated. The runner and verified pipeline are provided below for qualified external compute execution.

---

## 3. Execution Commands (Qualified Compute Environment)

### Step 3.1: Commit-Pinned External Execution

Use the clean Kaggle notebook `notebooks/aether_bfcl_official.ipynb`. It checks out
the recorded source commit, requires a separate human approval JSON bound to the exact
canonical config (`results/phase1/protocol_approvals/bfcl_official.json`) before
model download, verifies the exact wheel digest, verifies the retained
qualification manifest and every downloaded model/tokenizer file, and checks the
GPU/backend before model execution. It writes to `/kaggle/working`, then runs both
bundle verifiers and exports a tarball with a printed SHA-256. Preserve that hash
with the downloaded archive.

The canonical local preflight (which does not generate model output) uses:
```bash
python -m benchmarks.run_native_official bfcl --config configs/benchmarks/phase1_external.yaml \
  --snapshot-manifest /path/to/verified-model-snapshot-manifest.json \
  --package-wheel /path/to/bfcl_eval-2026.3.23-*.whl --approval results/phase1/protocol_approvals/bfcl_official.json \
  --output /tmp/aether-bfcl-preflight
```

The command fails closed if human approval, the pinned wheel, Linux GPU backend (including exact vLLM/Torch/CUDA versions, 15.0 decimal GB usable VRAM and capability 7.5+), or verified snapshot is unavailable. It never writes experiment artifacts inside the checkout.

### Step 3.2: Native Execution (only after preflight)
```bash
python -m benchmarks.run_native_official bfcl \
  --config configs/benchmarks/phase1_external.yaml \
  --snapshot-manifest /path/to/verified-model-snapshot-manifest.json \
  --package-wheel /path/to/bfcl_eval-2026.3.23-*.whl \
  --approval results/phase1/protocol_approvals/bfcl_official.json \
  --output /tmp/aether-bfcl-official --num-gpus 1 --backend vllm
```

### Step 3.3: Verification of Raw Outputs
```bash
python -m scripts.verify_bfcl_bundle /tmp/aether-bfcl-official
python -m scripts.verify_external_bundle /tmp/aether-bfcl-official --expected-kind bfcl_official
```

Transfer the archive and ingest atomically without overwriting existing evidence:
```bash
python -m scripts.ingest_external_bundle /path/to/aether-bfcl-official /path/to/results/phase1/bfcl/official --expected-kind bfcl_official
```

## 4. Expected Artifacts and Provenance

When executed on qualified compute, the output directory contains:
1. `command_records/plan.json` — Frozen plan and environment parameters
2. `command_records/command_0.json` — Generation command stdout/stderr/exit code
3. `execution_logs/command_1.json` — Evaluation command stdout/stderr/exit code
4. Raw per-category model outputs and evaluation scores for `simple`, `multiple`, `parallel`, `irrelevance`
5. `summary.json` — Conforming to schema `aether.nov19.external_benchmark.v1`
6. `manifest.json` — SHA-256 digests of all generated files
