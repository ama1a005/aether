# Qwen2.5 Pre-Projection Head Instrumentation

The installed Transformers Qwen2 attention implementation computes per-head attention output, transposes it to sequence-major layout, reshapes it to `[batch, sequence, num_attention_heads * head_dim]`, and passes that exact concatenated tensor to `self_attn.o_proj`. A forward pre-hook on `o_proj` is therefore the valid access point immediately before output projection mixes heads.

Head count and dimension are read from the loaded module/config, never hard-coded. For the pinned Qwen2.5-0.5B revision, the loaded values are 14 query heads and head dimension 64, reconstructing the 896-wide `o_proj` input. Captured heads have shape `[batch, sequence, heads, head_dim]`; reshaping them back must exactly reconstruct the captured concatenated input.

Passive acceptance requires identical greedy output and logits within the existing float32 tolerance. A head intervention clones the pre-projection tensor and replaces only one `[head, token]` slice before `o_proj`. Hooks must be removed after every run. Head search is conditional: at most one predeclared top attention layer per role may proceed, only if its parent attention component has rescue and induction at least 0.5 in both attack directions. No global layer-by-head-by-position sweep is permitted.
