# Real-Qwen development red-team protocol review

The prospective protocol is:

\`configs/experiments/qwen_red_team_development.yaml\`

SHA-256:

\`1c228f81c3bb77381149f5048fdd628502ba7072b2e52b7b8fce4189101fae58\`

## Frozen execution

- development split only;
- Qwen2.5-1.5B-Instruct revision
  \`989aa7980e4cf806f80c7fef2b1adb7bc71aa306\`;
- CUDA device 0 with float32 weights;
- deterministic one-token sender and receiver decisions;
- seed 42;
- one attack per declared family;
- at most 192 target calls;
- errors remain in denominators;
- every completed attempt is uploaded to a private Hugging Face dataset;
- validation and test executions remain zero.

This is supporting development robustness evidence. It is not causal-circuit,
remediation, validation, test, clinical or deployment evidence.

To authorize execution, independently hash the exact YAML and provide:

\`\`\`text
I approve real-Qwen red-team development protocol v1 SHA-256 1c228f81c3bb77381149f5048fdd628502ba7072b2e52b7b8fce4189101fae58
\`\`\`

No model access is permitted before that exact-hash approval is recorded.
