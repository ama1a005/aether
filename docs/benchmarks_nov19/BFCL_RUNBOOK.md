# BFCL Official Evaluation Runbook (AETHER Phase 1)

**Benchmark:** Berkeley Function Calling Leaderboard (BFCL)  
**Package:** `bfcl_eval==2026.3.23`  
**Package Wheel SHA-256:** `3bb6dfa5f0c68ad403c9ec50b00db2bb3b4cc9b38ab1ff33f48fe30d853d3a0a`  
**Target Model:** `Qwen/Qwen2.5-1.5B-Instruct`  
**Model Snapshot Revision:** `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`  
**Disclosed Custom Adapter:** `AETHER/Qwen2.5-1.5B-Instruct-FC`  
**Protocol Label:** `official_evaluator_with_disclosed_aether_model_adapter`  
**Configured Categories:** `simple`, `multiple`, `parallel`, `irrelevance` (`partial_evaluation: false`)  
**Target Output Directory:** `results/phase1/bfcl/official/`  

---

## 1. Scientific Role & Novelty Boundary

BFCL measures benign tool-use / function-calling competence.  
In AETHER:
- Upstream sender agent derives decisions from tool outputs.
- A failure to call tools correctly in clean scenarios would confound tool-poisoning attacks (an apparent attack success could simply be incompetence).
- BFCL establishes baseline benign function-calling accuracy on standard test sets.
- **Novelty boundary:** Running BFCL does NOT demonstrate DCMG causality, cross-agent circuit discovery, or remediation. It provides necessary external grounding.
- **Disclosed Adapter:** Because official `bfcl_eval` 2026.3.23 does not have a native Qwen2.5 configuration out-of-the-box, we register the custom adapter `AETHER/Qwen2.5-1.5B-Instruct-FC`. This is openly labeled in all paper-facing summaries and artifacts as a disclosed model adapter, NOT an unmodified leaderboard submission.

---

## 2. Hardware and Environment Requirements

- **OS:** Linux (Ubuntu 22.04+ recommended; Windows is incompatible with vLLM)
- **Python:** 3.11
- **Accelerator:** NVIDIA GPU with $\ge$ 16 GB VRAM (e.g. A100, RTX 4090, T4 x 2, or Kaggle P100/T4)
- **CUDA:** 12.1+
- **Inference Engine:** `vllm>=0.4.0` or `sglang`
- **Dependencies:**
  ```bash
  pip install "bfcl_eval==2026.3.23"
  pip install vllm
  pip install -e .
  ```

### Local Laptop Status (Laptop 2)
- Operating System: Windows 11
- Accelerator: CPU only (`torch.cuda.is_available() == False`, 0 GPUs)
- Status: **BLOCKED LOCALLY DUE TO HARDWARE CONSTRAINTS**.
- Gating Rule: The gate `bfcl_official` remains `MISSING` on this local machine. No synthetic or placeholder PASS file is generated. The runner and verified pipeline are provided below for qualified external compute execution.

---

## 3. Execution Commands (Qualified Compute Environment)

### Step 3.1: Preflight Verification & Dry-Run
```bash
python -m benchmarks.nov19_bfcl.runner --dry-run \
  --manifest results/phase1/model_qualification/qwen15b_kaggle_20261110/model_snapshot_manifest.json \
  --output-dir results/phase1/bfcl/official
```

### Step 3.2: Native Execution
```bash
python scripts/benchmark_bfcl_external_runner.py \
  --manifest results/phase1/model_qualification/qwen15b_kaggle_20261110/model_snapshot_manifest.json \
  --output-dir results/phase1/bfcl/official \
  --num-gpus 1 \
  --backend vllm
```

### Step 3.3: Verification of Raw Outputs
```bash
python -c "
from benchmarks.nov19_bfcl.verifier import BFCLArtifactVerifier
from benchmarks.nov19_bfcl.report import assemble_bfcl_summary
from pathlib import Path

verifier = BFCLArtifactVerifier(Path('results/phase1/bfcl/official'))
res = verifier.verify()
print('Verification passed:', res.passed)
if res.passed:
    summary = assemble_bfcl_summary(res, Path('results/phase1/bfcl/official/summary.json'))
    print('Summary written successfully')
else:
    print('Reasons:', res.reasons)
"
```

---

## 4. Expected Artifacts and Provenance

When executed on qualified compute, the output directory `results/phase1/bfcl/official/` contains:
1. `execution_logs/plan.json` — Frozen plan and environment parameters
2. `execution_logs/command_0.json` — Generation command stdout/stderr/exit code
3. `execution_logs/command_1.json` — Evaluation command stdout/stderr/exit code
4. Raw per-category model outputs and evaluation scores for `simple`, `multiple`, `parallel`, `irrelevance`
5. `summary.json` — Conforming to schema `aether.nov19.external_benchmark.v1`
6. `manifest.json` — SHA-256 digests of all generated files
