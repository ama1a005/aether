# Member 2: attacks, red team, MCPTox and TAMAS

**Branch:** `m2/attack-corpus`
**Deadline:** 20 November 2026, 10:30 Asia/Kolkata

## Mission and boundaries

Close `real_qwen_red_team`. Execute MCPTox/TAMAS as official evidence only when
upstream protocol, license, data and evaluator are verifiable. Never relabel
smoke, compatibility or transformed output as official evidence. Do not edit
target contracts, CORE-03, protected evaluation or SAE code.

## Relevant paths

- canonical red team: `experiments/phase1/qwen_red_team.py`
- config/notebook: `configs/experiments/qwen_red_team_development.yaml`,
  `notebooks/aether_qwen_red_team.ipynb`
- verifier/ingester: `scripts/verify_external_bundle.py`,
  `scripts/ingest_external_bundle.py`
- prior red-team helpers: `experiments/supporting_nov19/red_team/`
- MCPTox package: `benchmarks/nov19_mcptox/`
- TAMAS package: `benchmarks/nov19_tamas/`
- scripts: `scripts/benchmark_mcptox_external_runner.py`,
  `scripts/benchmark_tamas_external_runner.py`

Audit/reuse these implementations. Do not create competing pipelines.

## Step 1: branch and baseline

```bash
git fetch origin --prune
git switch lm
git pull --ff-only origin lm
git switch -c m2/attack-corpus
python -m pytest tests/unit/test_attacks.py \
 tests/unit/test_red_team_orchestration.py \
 tests/unit/test_qwen_red_team_backend.py \
 tests/unit/test_qwen_red_team_package.py \
 tests/unit/test_support_nov19_red_team.py \
 tests/unit/test_bench_nov19_mcptox.py \
 tests/unit/test_bench_nov19_tamas.py \
 tests/unit/test_bench_nov19_reporting.py \
 tests/integration/test_red_team_acceptance.py \
 tests/integration/test_red_team_mcp_backend.py \
 tests/integration/test_support_nov19_red_team_integration.py -q
```

Create `docs/handoffs/attacks/FINAL_SPRINT_START.md` with environment, upstream
access, credentials/resources, exact tests and blockers.

## Step 2: real-Qwen red team

1. Determine eligibility before model output.
2. Preserve frozen families, budgets, cases, seeds and stop rules.
3. Require the qualified immutable Qwen revision.
4. Retain clean/attacked pairs for every eligible case.
5. Record recon, planning, execution and debrief phases.
6. Save prompts, raw outputs, parsed decisions, tool calls, errors and latency.
7. Keep invalid/error attempts in ASR denominators.
8. Atomically checkpoint every completed attempt.
9. Resume without replaying completed attempts or dropping partial failures.
10. Keep validation/test counts zero.
11. Independently verify exact case coverage, hashes and real-model evidence.
12. Report red-team robustness separately from causal-circuit claims.

## Step 3: MCPTox source and license audit

Before execution, write a machine-readable audit containing:

```text
official repository URL and exact revision
retrieval time
license path/hash and permitted use
dataset manifest/hash
official evaluator entry point
official case IDs/subset
required MCP servers and versions
model/provider requirements
credentials
native output schema
```

Independently verify old handoff statements. If no usable license exists, stop
with `BLOCKED_LICENSE`. Do not infer permission.

If authorized, prospectively freeze task IDs, model, server images, seeds,
attack-success definition, denominators, budgets and failure handling. Obtain
exact human approval for any newly frozen scientific protocol. Then:

1. execute the official/native evaluator;
2. retain untouched native output;
3. import through deterministic disclosed code;
4. cross-check native/imported totals;
5. verify hashes, coverage and denominators independently;
6. ingest atomically into `results/phase1/mcptox/official`.

Never use the local MCPTox smoke to close the official gate.

## Step 4: TAMAS source and execution audit

Record the same provenance plus native multi-agent framework/version,
provider/API requirements, judge type, judge model/revision/prompts, attack
paradigms, retry/rate limits, cost and credentials.

Do not replace unavailable native AutoGen/CrewAI/provider behavior with a local
simulation. If authorized, freeze the protocol, retain raw conversations and
judge records, separate deterministic and LLM-judge endpoints, independently
verify and ingest atomically. Otherwise document the exact blocker and leave the
official gate missing.

## Step 5: unified reporting

Use `benchmarks/nov19_reporting/` only on artifact-specific verified bundles.
It must reject incomplete input, retain denominators/errors, use declared
confidence intervals, account for correlated repeats, label official versus
compatible/synthetic evidence, and never combine incomparable benchmark
metrics. Generate tables from artifacts, not manually copied numbers.

## Required final tests

```bash
python -m pytest tests/unit/test_attacks.py \
 tests/unit/test_red_team_orchestration.py \
 tests/unit/test_qwen_red_team_backend.py \
 tests/unit/test_qwen_red_team_package.py \
 tests/unit/test_support_nov19_red_team.py \
 tests/unit/test_bench_nov19_mcptox.py \
 tests/unit/test_bench_nov19_tamas.py \
 tests/unit/test_bench_nov19_reporting.py \
 tests/integration/test_red_team_acceptance.py \
 tests/integration/test_red_team_mcp_backend.py \
 tests/integration/test_support_nov19_red_team_integration.py -q
```

## Definition of done

- Real-Qwen red-team bundle verifies.
- MCPTox/TAMAS have genuine official bundles or evidence-backed blockers.
- No compatibility output is promoted as official.
- Final handoff records every source, license, revision, command, test count,
  artifact hash, supported claim and limitation.

