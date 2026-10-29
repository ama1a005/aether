# Qwen execution options — 2026-10-29

There are two independent problems: sufficient resources to execute, and model
behavior suitable for the experiment. CUDA installation proves neither. The
0.5B V2 development results failed the behavioral prerequisite. The 1.5B model
has not yet earned qualification; more RAM cannot guarantee MQ-G1/MQ-G2 pass.

## Recommended route preserving current experimental choices

Use the other laptop (or an institution-owned workstation) with sufficient
available RAM. Keep Python 3.11, the locked environment, CPU float32, the same
prompts/cases/parser/generation parameters, and the frozen numerical gates.
A 32 GiB RAM machine is a reasonable headroom target, not a measured guarantee.
Run the model-free preflight on that machine: installed >=15 GiB, available
>=10.5 GiB, cache disk >=12 GiB. Require >=2 GiB available after loading.

Freeze the exact model and tokenizer commit and hashes before execution. Current
MQ files name Qwen2.5-1.5B-Instruct but do not provide that immutable revision.
Use low_cpu_mem_usage=True, model.eval(), and the prescribed one-model loading
policy. Preserve all qualification failures, including resource failures.
After MQ-G1 and MQ-G2 pass, instrumentation acceptance is still a separate gate.
Moving hardware requires recording hardware/library differences; bitwise equality
across CPU platforms must be checked, not assumed.

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
