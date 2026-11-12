# Qwen execution options — 2026-10-29

> **Status update, 2026-11-12:** The 1.5B model subsequently passed
> qualification, instrumentation acceptance and development capture. QCI-1.1
> then completed with no supported internal candidate because every candidate
> failed at least one frozen predicate, most importantly shuffled-source
> specificity. The binding state is `STOP_NO_SUPPORTED_CANDIDATE`; do not run
> QCI-A1 or treat the historical “pending qualification” text below as current.

There are two independent problems: sufficient resources to execute, and model
behavior suitable for the experiment. CUDA installation proves neither. The
0.5B V2 development results failed the behavioral prerequisite. The 1.5B model
has not yet earned qualification; more RAM cannot guarantee MQ-G1/MQ-G2 pass.

## Recommended route preserving current experimental choices

The prepared Kaggle route uses Python 3.11.9, the checked-in lock, CPU float32,
no quantization/offload, and the frozen prompts/cases/parser/generation parameters.
Any attached T4 devices remain unused: MQ-HW1 explicitly requires CPU execution.
The notebook measures the installed/available memory and cache-drive space before
accessing the model, then requires at least 2 GiB available after loading. It also
checks cgroup headroom when Kaggle exposes that limit.

RD-029 pins the sole candidate to official Qwen commit
`989aa7980e4cf806f80c7fef2b1adb7bc71aa306`. The notebook hashes the downloaded
snapshot and uses `low_cpu_mem_usage=True`, `model.eval()`, and one load attempt.
The runner evaluates MQ-G1 first and runs MQ-G2 only on MQ-G1 pass. If either
fails, preserve the result and stop. Passing both permits only a separately
reviewed instrumentation-acceptance stage. The Kaggle execution and outcomes
remain pending user action; no model has been downloaded by this preparation.

## Alternatives and what changes

| Option | Scientific impact / protocol status |
|---|---|
| Close unrelated applications/reboot, or add physical RAM | Preserves model/numerics; remeasure actual headroom. Do not terminate unidentified user processes. |
| Larger local or remote CPU machine running this repository | Best route for preserving the frozen CPU fp32 setup; remote execution must expose hooks and artifacts. Cloud spending requires authorization. |
| Low-memory loading | Already permitted by MQ-HW1; reduces load duplication, not the final weight/activation footprint. |
| GPU float32 | Same nominal precision but different numerical kernels; current MQ-HW1 forbids migration. Requires prospective amendment and equivalence/non-interference tests. Historical GPU is only 4 GiB, insufficient for roughly 6 GB fp32 weights alone. |
| GPU fp16/bfloat16 | Reduces weight storage, changes numerical behavior. Requalify and recalibrate under a new execution protocol; 4 GiB is tight once caches/activations are included. |
| CPU/disk offloading | Transformers/Accelerate support it; hook/device behavior, runtime and memory must be verified. Explicit/disk offload is prohibited by current MQ-HW1. |
| Quantization | Changes weights/activations and potentially causal effects; separate validated condition, not an interchangeable substitute. |
| Different/smaller model | May load but may fail the behavioral task. Requires prospective selection/qualification; never silently substitute after observing outcomes. |
| Hosted text API | Useful for behavioral benchmark comparisons, but cannot replace white-box activation hooks and interventions unless the service exposes the required internals. |
| Page-file increase | Not a substitute for physical headroom and explicitly prohibited in MQ-HW1. |

Sources consulted: https://huggingface.co/docs/transformers/main/big_models and
https://huggingface.co/docs/accelerate/usage_guides/big_modeling . Repository
authority: configs/model_qualification/v2_mq_hw1.json and the frozen MQ protocols.
No alternative was executed or model weight downloaded during this audit.
