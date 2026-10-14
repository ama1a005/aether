# TAMAS Integration

## Source identity

- Official repository: `https://github.com/microsoft/TAMAS`
- Pinned commit: `545c112af9aab93b7ef2b0b60831d93c81c365c3`
- Paper: *TAMAS: Benchmarking Adversarial Risks in Multi-Agent LLM Systems*, arXiv `2511.05269`
- Code license: MIT
- Data license: CDLA-Permissive-2.0
- Loaded release: 300 adversarial records, 50 each for Byzantine, Colluding, Contradicting, DPI, Impersonation, and IPI.

The adapter preserves each native agent list, agent description, user query, attack type, and scenario. Its smoke serializes ten records and validates the full 300-record identity without model execution.

## Compatibility boundary

TAMAS natively executes AutoGen or CrewAI configurations and evaluates their logs with attack-specific scripts. Provider-backed paths require API credentials; local execution assumes Ollama. Some evaluation paths use LLM assessment. AETHER's two-agent Qwen harness is not either native framework. Running TAMAS records through it would therefore be an `aether_transformed` result, not an official-compatible TAMAS score.

No native TAMAS scenario was run in this checkpoint. This is adapter readiness only; no credentials or framework dependencies were added.
