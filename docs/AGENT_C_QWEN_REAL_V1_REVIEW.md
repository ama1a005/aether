# Real-Qwen Agent C development protocol v1 — human review gate

## Decision requested

Review the immutable proposal at
`configs/experiments/agent_c_qwen_real_development_v1.yaml`.

This proposal is intentionally separate from the existing deterministic
Agent C supporting result. No implementation or model execution is authorized
until a human reviewer approves the exact proposal hash.

## What is being proposed

The experiment adds a genuinely Qwen-powered third agent to the retained
two-agent development traces. For each of the 24 frozen development cases, it
reviews both the clean and attacked Agent B decision, producing 48 paired rows.

Agent C receives:

- the case ID;
- the clean or attacked mediator message from the retained real-Qwen run;
- Agent B's incoming decision; and
- vital signs returned through a real MCP SDK stdio session.

It does **not** receive the ground-truth decision. Ground truth is joined only
after generation by the evaluator.

The model must first emit the single frozen `get_vital_signs` tool request. The
runner calls the discovered MCP tool, adds the returned evidence to the
conversation, and asks Qwen for one strict final JSON review. There are no
semantic retries or fallback transports. Invalid output is retained and counts
as incorrect.

## Why the existing Agent C result is not enough

`results/phase1/agent_c/development` uses real-Qwen Agent A/B inputs but a
deterministic policy for Agent C. It is useful supporting evidence, but it does
not test a third Qwen agent. It remains immutable and cannot satisfy the
`real_qwen_agent_c` completion gate.

The new proposal does not relabel or overwrite that result.

## Frozen scientific choices

- Model and tokenizer: `Qwen/Qwen2.5-1.5B-Instruct` at revision
  `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`.
- Split: development only.
- Cohort: the exact 24 case IDs listed in the proposal.
- Conditions: clean and attacked for every case.
- Input artifacts: exact retained Qwen rows, source manifest and case registry
  hashes.
- Decoding: deterministic, seed 0, at most two generations per row.
- Tool: one discovered `get_vital_signs` call over MCP stdio; no fallback.
- Invalid policy: retain, no retry, count as incorrect.
- Metrics: paired accuracy, invalidity, corrections, regressions, McNemar and a
  paired bootstrap interval.
- No post-hoc performance threshold. `PASS` means execution integrity only,
  never that the model improved performance.
- Validation and test access remain zero.

## Required implementation after approval

Only after exact-hash approval, implement:

1. a strict proposal loader and preflight;
2. the isolated MCP stdio vital-sign server;
3. the Qwen Agent C two-generation runner;
4. per-row atomic and remote checkpointing;
5. an independent bundle verifier;
6. an atomic ingester that refuses overwrite;
7. a commit-pinned Kaggle notebook;
8. model-independent tests for every failure boundary; and
9. frontend/report integration that consumes only a verified ingested bundle.

Production evidence must reject mocks, synthetic rows, dirty source trees,
wrong model revisions, changed inputs, malformed prefixes, missing tool calls,
fallback transports, protected-split access and incomplete runs.

## Claims permitted if an approved run completes

The project may report the measured development-only behavior of a real Qwen
third-agent reviewer under the frozen AETHER protocol. It may compare incoming
and reviewed decisions on the paired retained cohort.

It may not claim:

- held-out generalization;
- clinical validity;
- official benchmark performance;
- causal-circuit evidence;
- remediation efficacy; or
- that a completed run improved accuracy unless the reported estimates support
  that statement.

## Human checklist

- [ ] The model and revision are acceptable.
- [ ] The 24 development cases and both conditions are acceptable.
- [ ] Ground truth is unavailable to Agent C.
- [ ] MCP semantics and the absence of fallback are acceptable.
- [ ] Prompts and strict output schema are acceptable.
- [ ] Invalid outputs remain in denominators.
- [ ] Metrics and the no-performance-threshold decision are acceptable.
- [ ] Checkpoint/resume rules are acceptable.
- [ ] Validation/test counts remain zero.
- [ ] The deterministic supporting bundle remains distinct.
- [ ] The claim boundary is acceptable.

## Approval form

After independently computing the SHA-256 of the exact proposal file, the
human project owner may respond:

```text
I approve real-Qwen Agent C development protocol v1 SHA-256 <EXACT_HASH>
```

The coding agent must not create or impersonate this decision.
