# Sender Generation-Step Intervention

The V2 sender emits the decision code as its first generated token. Generation step `0` is therefore the forward computation whose final-position logits predict `decision_code`. The stored trace records the original prompt token IDs, all generated token IDs, decision token index `prompt_length`, generation step `0`, the prompt prefix before that decision, and the post-decision token generated at step `1`.

Causal generation uses an explicit greedy loop with `use_cache=False`. At each step the model receives the full prefix; the adapter exposes the active step to hooks. A generation-step patch fires only at the declared step and replaces the selected module's last-token state before logits and greedy selection. This removes ambiguity about KV-cache reuse. Standard cached `generate` is used only as a non-interference/equivalence reference.

The primary sender position is decision-generation step `0`. There is no evidence-field generation step in the one-token mediator schema. Step `1`, after the decision token is already fixed, is the predeclared irrelevant generation control. Teacher-forced prompt-plus-output activations may guide alignment but are associative only; final sender evidence must come from actual uncached autoregressive generation.

Acceptance tests require exact standard/uncached greedy equality, intended-step-only firing, passive non-interference, local replacement, hook cleanup, no accumulation, and explicit no-cache semantics. Disabling caching increases sender intervention compute because the full prefix is recomputed at every generated step; V2 bounds generation to two tokens.
