# Hardware Profile

**Captured:** 2026-10-12 Asia/Calcutta
**Purpose:** Phase-1 real-model development selection

## CPU and memory

- CPU: 12th Gen Intel Core i5-12500H
- Physical cores: 12
- Logical processors: 16
- Installed RAM: 16,825,634,816 bytes (15.67 GiB)
- Available RAM at inventory: 1,949,155,328 bytes (1.82 GiB)

Available memory is a transient measurement. Real-model runs must record their own observed memory and avoid concurrent memory-heavy applications.

## GPU

- Discrete GPU: NVIDIA GeForce RTX 2050 Laptop GPU
- VRAM: 4,096 MiB
- Free VRAM at inventory: approximately 4,024 MiB (`nvidia-smi`: 72 MiB used)
- Driver: 591.74
- Driver-reported maximum CUDA compatibility: 13.1
- Compute mode: Default; WDDM
- Integrated GPU: Intel Iris Xe Graphics

## PyTorch

- PyTorch: 2.14.1+cpu
- CUDA available to PyTorch: false
- PyTorch CUDA runtime: none
- CUDA device visible to PyTorch: none
- CUDA bf16 report: unsupported in the installed CPU build

The machine has an NVIDIA GPU and working driver, but the repository environment currently contains CPU-only PyTorch. No CUDA toolkit or driver change was attempted.

## Disk

- Repository/Hugging Face cache drive: `C:`
- Total: 372,953,649,152 bytes (347.34 GiB)
- Free at inventory: 18,110,173,184 bytes (16.87 GiB)

## Development implication

Qwen2.5-1.5B is not a comfortable unquantized intervention target on this configuration: fp32 weights alone are roughly 6 GB, before runtime and activation memory, and current PyTorch cannot use the GPU. Qwen2.5-0.5B is selected for the first CPU-backed instrumentation milestone. Initial capture is restricted to selected layer/block, attention-output, and MLP-output tensors. Quantization is excluded from the initial causal pipeline.

## Observed real-model run

- Execution: fp32 CPU; observed VRAM use by PyTorch: none
- Process RSS before load: 227,110,912 bytes
- Process RSS after load: 2,440,650,752 bytes
- Process RSS after experiment: 2,517,397,504 bytes
- Peak process working set: 2,546,548,736 bytes (2.37 GiB)
- Model load: 8.77 seconds; total smoke: 10.22 seconds on the recorded regeneration

The model registry estimates fp32 parameter storage at approximately 1.84 GiB (`494,032,768 * 4` bytes); observed peak process memory includes Python, PyTorch, model, inference tensors, and captured activation.
