# Member 1 final sprint handoff

## Current identity

- Owner: Member 1 — target and protocol
- Branch: `m1/target-harness`
- Integrated `lm` merge commit: `ecf5be3`
- Integration/portability repair: `c7d5bfa`
- Real-Qwen Agent C proposal commit: `3aaa6f2`
- Real-Qwen Agent C implementation commit: `27ee9dc`
- BFCL notebook commit: `b796d81`
- Date: 2026-11-20

The branch was integrated by merging `origin/lm`; history was not rebased or
rewritten. Frozen CORE evidence was not rerun or replaced.

## What is implemented and verified

### Target harness

The deterministic target harness produces run-scoped traces, CSV output,
reproducibility metadata and structured logs. It now also prints the computed
`Clean Pass Rate` and `Attack Success Rate` summaries required by the review
regression interface. These are deterministic plumbing results, not model or
benchmark evidence.

### Official BFCL execution package

The branch contains the pinned `bfcl_eval==2026.3.23` identity and wheel hash,
the disclosed AETHER Qwen2.5 function-calling adapter, native official
generation/evaluation orchestration, strict preflight, two verifiers, atomic
ingestion infrastructure and `notebooks/aether_bfcl_official.ipynb`.

The notebook is pinned to source commit
`3aaa6f2b25d7794fd0d1990bcd2ae85a1d65be33`. It verifies the approved config
before model download, installs and hashes the official wheel, checks the GPU
backend, verifies the qualified Qwen snapshot and retains failed attempts
instead of inventing a score.

### Existing Agent C supporting evidence

The bundle at `results/phase1/agent_c/development` independently verifies:

```text
experiment_id: P0_agent_c_qwen15b_development
run_id: P0_agent_c_qwen15b_development_20261119_e16d3603_02
case_count: 24
condition_rows: 48
verified: true
```

It uses retained real-Qwen Agent A/B traces with deterministic clean-tool
Agent C. It is supporting evidence only, not a Qwen-powered third agent, and
cannot satisfy `real_qwen_agent_c`.

### Approved genuine Qwen Agent C

The separate candidate protocol is:

```text
configs/experiments/agent_c_qwen_real_development_v1.yaml
SHA-256: 9e031fb2911686702e28ec00b54299e01d428a1d2e1676050d0b3dc541d392a7
```

Human review material is in `docs/AGENT_C_QWEN_REAL_V1_REVIEW.md`.

It freezes a genuine Qwen Agent C, 24 development cases, paired clean/attacked
review, real MCP stdio discovery/tool execution, strict JSON output, no
ground-truth access, invalid-as-incorrect denominators, per-row checkpointing,
protected-split locks and honest execution-PASS semantics.

The human project owner approved the exact hash on 2026-11-19/20. The approval
artifact, strict loader, Qwen runner, real MCP stdio server/client, independent
verifier, atomic ingester and checkpoint-safe Kaggle notebook are implemented.
The implementation is pinned in
`notebooks/aether_qwen_agent_c_real.ipynb` to commit
`27ee9dc2b1a8e6cbbfef50cf7760a0ad1a852ab8`. No model execution has occurred.

### Cross-platform frozen evidence

Older validators compared raw text bytes, causing unchanged LF Kaggle checkouts
and CRLF Windows checkouts to disagree. Validators now accept only raw identity
or newline-only UTF-8 equivalence for declared text artifacts. Content changes
still fail closed. This covers QCI/CORE verifiers, method-freeze inputs and
external protocol approvals.

### Demo

Python unit, integration and regression coverage passes, including real MCP
stdio integration. The package verifier correctly refuses to claim a production
package when `demo/frontend/dist` is absent.

In this isolated worktree, frontend installation could not finish because npm
10.9.2 failed internally and the registry retry ended with `ECONNRESET`. No
fallback was introduced, and a build from a different lockfile was not reused.

## Exact verification results

Final integrated unit suite, including the prospective protocol checks:

```text
655 passed, 0 failed, 0 skipped
```

BFCL package/notebook focused suite:

```text
34 passed, 0 failed, 0 skipped
```

Integration:

```text
24 collected; 19 passed; 5 skipped; 0 failed
```

The five skips are declared unavailable real-model or live-demo-service gates,
not passed evidence.

Regression:

```text
6 passed, 0 failed, 0 skipped
```

Retained Agent C verification commands both pass:

```powershell
python -m scripts.verify_agent_c_bundle results/phase1/agent_c/development
python -m scripts.verify_external_bundle `
  results/phase1/agent_c/development `
  --expected-kind qwen_agent_c
```

## Completion gates

| Gate | Current state | Meaning |
|---|---|---|
| Target harness | Implemented and tested | Deterministic plumbing works |
| Deterministic Agent C | Verified supporting evidence | Not a third Qwen agent |
| Official BFCL | Execution package ready | No official result yet |
| Real-Qwen Agent C | Approved and implemented | External execution pending |
| Demo package | Python paths verified; frontend rebuild blocked | No false PASS |

## Manual actions

### 1. Execute real-Qwen Agent C

After the branch is pushed, upload
`notebooks/aether_qwen_agent_c_real.ipynb` to Kaggle, enable a T4 or better GPU,
Internet and the `HF_TOKEN` plus `AETHER_HF_REPO` secrets. The Hugging Face
repository must already exist and be private. Run all cells unchanged. Each of
the 48 case-condition units is uploaded immediately; a restarted session
continues from the exact next row. Return the final archive for verification and
atomic ingestion into `results/phase1/agent_c/qwen15b`.

### 2. Execute official BFCL

After this branch is pushed, upload
`notebooks/aether_bfcl_official.ipynb` to compatible Linux/CUDA compute. Use a
new unique attempt ID, run all cells unchanged, retain the archive even on
failure, and return it for independent verification and atomic ingestion.

### 3. Rebuild the frontend when npm access works

```powershell
Set-Location demo/frontend
npm.cmd ci
npm.cmd test -- --run
npm.cmd run build
Set-Location ../..
python -m scripts.verify_demo_package
```

Do not commit `node_modules`, npm caches or generated experiment outputs.

## Supported claims and non-claims

Supported:

- target and official-execution infrastructure are implemented and tested;
- the deterministic Agent C bundle verifies with real-Qwen A/B provenance;
- the BFCL notebook is pinned and fail-closed; and
- the approved genuine Qwen Agent C package is implemented and fail-closed.

Not supported:

- no official BFCL score exists;
- deterministic Agent C is not a Qwen third agent;
- genuine Qwen Agent C has not yet been externally executed;
- readiness is not scientific evidence; and
- no protected validation/test split was accessed by this work.

## Integration checklist

- [x] Latest `lm` merged without history rewrite.
- [x] Full integrated unit suite had zero failures.
- [x] Integration and regression suites have zero failures.
- [x] Completion gates were not weakened.
- [x] Deterministic Agent C remains supporting-only.
- [x] BFCL notebook is repinned to integrated source.
- [x] No mock/synthetic result was promoted as evidence.
- [x] No model or official dataset was downloaded locally.
- [x] Human approval for genuine Qwen Agent C v1.
- [x] Real-Qwen Agent C implementation and model-independent verification.
- [ ] Real-Qwen Agent C external execution, verification and ingestion.
- [ ] Official BFCL execution, verification and ingestion.
- [ ] Fresh frontend production build and package verification.
- [ ] Teammate review before merge into `lm`.
