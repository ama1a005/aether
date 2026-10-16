# V2 Model Qualification Hardware Retry Protocol

**Status:** MQ-HW1 PROSPECTIVELY FROZEN BEFORE RETRY MEASUREMENT

This additive protocol preserves `docs/MODEL_QUALIFICATION_PROTOCOL.md` byte-for-byte at SHA-256 `64badcea20c43ba7a42f3b8134aa261805484d4bff38841a7130584108827c89`. It changes only the host-resource prerequisite for the one authorized `Qwen/Qwen2.5-1.5B-Instruct` qualification campaign. MQ-G1, MQ-G2, V2, prompts, attacks, parser, model, and split locks remain unchanged.

## MQ-HW1 predicates

Before any model repository, tokenizer, or weight access:

1. Installed physical RAM is at least 15.0 GiB.
2. Available physical RAM is at least 10.5 GiB.
3. Free space on the model/cache drive is at least 12.0 GiB.
4. Execution remains CPU, float32, unquantized, and without explicit model or disk offload.
5. No page-file manipulation, CUDA installation, or GPU migration is permitted.
6. `low_cpu_mem_usage=True` is permitted because it changes loading behavior rather than numerical semantics.

All three resource predicates are conjunctive. A near miss does not pass. If pre-access RAM or disk fails, stop without model access and request manual memory cleanup where applicable. Pre-model checks may be repeated only after manual cleanup because no model outcome has been observed.

After the single successful model-load attempt, available physical RAM must remain at least 2.0 GiB before behavioral inference. Otherwise unload where practical and record `BLOCKED_AFTER_LOAD`. A `MemoryError`, allocation failure, or clearly memory-related load failure records `BLOCKED_MEMORY_RUNTIME`; the load is not automatically retried.

The machine-readable authority is `configs/model_qualification/v2_mq_hw1.json`. Once model access and behavioral execution begin, an unfavorable result may not reset the campaign.
