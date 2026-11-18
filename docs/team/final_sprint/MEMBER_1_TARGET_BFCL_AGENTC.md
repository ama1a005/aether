# Member 1: target harness, BFCL, Agent C and demo

**Branch:** `m1/target-harness`
**Deadline:** 20 November 2026, 10:30 Asia/Kolkata

## Mission and boundaries

Close as much of `bfcl_official` and `real_qwen_agent_c` as genuine external
execution permits, and make the review demo reproducibly launchable. Do not edit
CORE-03, protected evaluation protocols, attack labels, SAE code or contracts.

## Canonical paths

- BFCL entry: `benchmarks/run_native_official.py`
- BFCL verifier/ingester: `scripts/verify_external_bundle.py`,
  `scripts/ingest_external_bundle.py`
- BFCL notebook: `notebooks/aether_bfcl_official.ipynb`
- Agent C entry: `experiments/phase1/qwen_agent_c.py`
- Agent C config/notebook: `configs/experiments/agent_c_qwen_development.yaml`,
  `notebooks/aether_qwen_agent_c.ipynb`
- prior teammate helpers: `benchmarks/nov19_bfcl/`,
  `experiments/supporting_nov19/agent_c/`

The completion-registry entry is canonical. Audit and reuse the `nov19` helpers;
do not create a third runner. Document any superseded path.

## Step 1: branch and baseline

```bash
git fetch origin --prune
git switch lm
git pull --ff-only origin lm
git switch -c m1/target-harness
python -m pytest tests/unit/test_target.py \
 tests/unit/test_bfcl_qwen25_adapter.py \
 tests/unit/test_native_official_package.py \
 tests/unit/test_bench_nov19_bfcl.py \
 tests/unit/test_qwen_agent_c.py \
 tests/unit/test_support_nov19_agent_c.py \
 tests/integration/test_target_pipeline.py \
 tests/integration/test_support_nov19_agent_c_integration.py -q
```

Write `docs/handoffs/target/FINAL_SPRINT_START.md` with commit, Python/package
versions, compute, test count and missing credentials.

## Step 2: BFCL readiness audit

Read `docs/benchmarks_nov19/BFCL_RUNBOOK.md` and inspect all canonical code.
Before official execution, verify:

1. official BFCL package version and wheel hash are pinned;
2. exact subset/task IDs were fixed before results;
3. frozen Qwen model and tokenizer revisions are checked;
4. every snapshot file hash is verified;
5. the disclosed adapter delegates to BFCL's own Qwen function-calling handler;
6. official generation and evaluator commands are retained;
7. native raw generation and evaluation outputs remain unmodified;
8. invalid/error cases stay in denominators;
9. dirty Git, altered config, wrong model or missing approval fail before access;
10. the claim label says `official evaluator with disclosed AETHER adapter`,
    never “unmodified leaderboard configuration.”

Required retained artifacts:

```text
manifest.json
preflight.json
official_generation_output.*
official_evaluation_output.*
summary.json
archive_contents.json
```

The manifest must contain every reproducibility field from `AGENTS.md`. The
summary must include official-evaluator status, adapter disclosure, exact model,
subset totals, invalid/error counts and validation/test counts.

Run on Linux/Kaggle GPU if the official stack requires CUDA/vLLM. Pin the
notebook to the reviewed commit. Save large output outside Git, compute SHA-256,
run the independent verifier, and provide the final archive. If the official
evaluator is unavailable, document the exact blocker; never promote a
compatibility score.

## Step 3: real-Qwen Agent C

Audit `target/three_agent_pipeline.py` and the canonical runner. Ensure:

1. Agent B raw decision is immutable and stored separately;
2. Agent C receives the logged decision, message and case;
3. clean and attacked conditions use identical eligibility;
4. only declared development cases run;
5. model/revision, prompts, token IDs, generation parameters and seeds are saved;
6. raw output, parsed review, tool calls, latency and errors are retained;
7. each case/condition checkpoints atomically;
8. restart cannot duplicate or silently drop a unit;
9. validation/test execution counts are zero;
10. Agent C is labelled supporting evidence, not causal-core evidence.

Derive summaries from raw records. Verify exact case coverage and hashes before
atomic ingestion. Do not set PASS from fixtures or deterministic smoke output.

## Step 4: demo packaging

```bash
python scripts/verify_demo_package.py
python -m pytest tests/unit/test_review_demo.py \
 tests/integration/test_review_demo_e2e.py -q
cd demo/frontend
npm ci
npm test -- --run
npm run build
```

Manually verify backend health, MCP stdio, explicit external-MCP failure, demo
case selection, clean trace, attack lab, causal analysis, evidence status and
absence of fake PASS states. Write `docs/handoffs/target/DEMO_FINAL_RUNBOOK.md`
with Windows/Linux startup, ports, expected health output and shutdown.

## Required final tests

```bash
python -m pytest tests/unit/test_target.py \
 tests/unit/test_bfcl_qwen25_adapter.py \
 tests/unit/test_native_official_package.py \
 tests/unit/test_bench_nov19_bfcl.py \
 tests/unit/test_qwen_agent_c.py \
 tests/unit/test_support_nov19_agent_c.py \
 tests/integration/test_target_pipeline.py \
 tests/integration/test_support_nov19_agent_c_integration.py \
 tests/integration/test_review_demo_e2e.py -q
```

## Definition of done

- BFCL official bundle verifies, or a precise external blocker is retained.
- Real Agent C bundle verifies and preserves Agent B output.
- Demo automated and manual checks pass.
- Handoff includes commits, commands, exact tests, artifacts/hashes, supported
  claims, non-claims and manual integration actions.

