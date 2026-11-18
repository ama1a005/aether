# AETHER Phase-1 final sprint master plan

**Deadline:** 20 November 2026, 15:00 Asia/Kolkata
**Integration branch:** `lm`
**Frozen starting commit:** `0d20dec897d9844336ebb5e9fcdc6c9ec33b2663`
**Audience:** four project members and their coding agents

## 1. Mandatory reading

Read completely, in order, before editing:

1. `AGENTS.md`
2. `RESEARCH_CONTRACT.md`
3. `PROJECT_STATE.md`
4. `TASK.md`
5. `docs/team/COMPLETE_PROJECT_STUDY_GUIDE.md`
6. `docs/team/team_ownership.yaml`
7. this master plan
8. the assigned brief under `docs/team/final_sprint/`

The frozen contract wins over every guide. Independently verified artifacts win
over planning documents. Fixtures, mocks, smoke tests and prepared runners are
software evidence, not scientific results.

## 2. Branch setup

No member works directly on `main` or `lm`.

```bash
git fetch origin --prune
git switch lm
git pull --ff-only origin lm
git rev-parse HEAD
```

Create exactly one owner branch:

```bash
# M1
git switch -c m1/target-harness

# M2
git switch -c m2/attack-corpus

# M3
git switch -c m3/mech-interventions

# M4
git switch -c m4/cross-agent-graph
```

Push only that branch. Do not merge another member branch. Do not force-push
after review begins. The integration owner merges reviewed commits into `lm`.

## 3. Split and conflict boundaries

| Member | Delivery | Branch | Primary paths |
|---|---|---|---|
| M1 | target harness, BFCL, Agent C, demo | `m1/target-harness` | `target/`, `configs/experiments/` |
| M2 | attack evaluation, red team, MCPTox, TAMAS | `m2/attack-corpus` | `attacks/`, `data/attack_cases/`, `benchmarks/` |
| M3 | trained SAE, second model | `m3/mech-interventions` | mechanistic/intervention code |
| M4 | CORE-03, validation/test, final report | `m4/cross-agent-graph` | `causal/`, `experiments/phase1/` |

Only M4/integration edits `PROJECT_STATE.md`, `TASK.md`, completion registries,
or final evidence UI unless coordination is explicit. Other members write
handoffs in their owned `docs/handoffs/<area>/` directory.

## 4. Immutable scientific checkpoint

Already complete: Qwen qualification, instrumentation acceptance, development
capture, QCI-1 negative result, QCI-2 semantic discovery/audit, method freeze,
CORE-02 matched search, Tracr calibration and IOI calibration.

CORE-02 found `message.decision_code` sufficient across all three seeds. The
receiver-only comparator selected `receiver.head.L20.H5.pre_o_proj` with lower
faithfulness. This does not establish a connected internal DCMG, global
minimality, search superiority or a deployable defense.

CORE-03 is active under approved proposal SHA-256:

```text
cd96984e161389cdbff347dc317f04eaa78ea697689f25620f6566f8bc6803b7
```

## 5. Dependencies that cannot be parallelized

```text
CORE-03 verified result
 -> locked-validation protocol freeze
 -> exact human approval
 -> locked-validation execution and ingestion
 -> once-only-test protocol freeze
 -> exact human approval
 -> once-only test
 -> final evidence report
```

Other independent tracks may run in parallel:

```text
Qwen qualification -> BFCL
CORE-02 -> red team
CORE-02 -> Agent C
development capture + trained checkpoint -> SAE evaluation
once-only primary test -> second-model evidence promotion
```

## 6. Schedule

### 18 November

- M4: finish/ingest CORE-03.
- M1: audit BFCL and Agent C, run model-free gates, start external execution.
- M2: audit red team; resolve official MCPTox/TAMAS sources and licenses.
- M3: locate real activation tensors, verify hashes, audit SAE compatibility.

### 19 November

- M4: freeze, approve, implement and execute locked validation.
- M1: execute BFCL and Agent C; retain and verify bundles.
- M2: execute red team and any authorized official benchmark.
- M3: train/evaluate SAE only after exact protocol approval; prepare second model.

### 20 November morning

- M4: ingest validation, freeze and run once-only test, generate final report.
- M1/M2/M3: finish verifiers, documentation and handoffs by 10:30.
- Integration: merge reviewed work, run full Python/frontend/smoke checks.

### 20 November 12:30-15:00

No new methods. Finalize documentation, tables, figures, presentation, backups
and the final tagged checkpoint.

## 7. Rules for every evidence runner

1. Validate config and exact approval before model/data access.
2. Refuse dirty source for evidence execution.
3. Record every reproducibility field required by `AGENTS.md`.
4. Preserve invalid/error rows in denominators.
5. Checkpoint atomically at the smallest safe unit.
6. Resume completed units without silently skipping partial units.
7. Keep raw outputs separate from summaries.
8. Hash every retained artifact in `archive_contents.json`.
9. Provide an independent verifier.
10. Provide atomic ingestion that refuses overwrite.
11. Define execution PASS separately from scientific success.
12. Retain negative, incomplete and failed outcomes.

## 8. Required handoff

Create `docs/handoffs/<area>/FINAL_SPRINT_HANDOFF.md` containing:

```text
owner and branch
base lm commit
final commits
files changed
commands executed
exact tests passed/failed/skipped
external resources and revisions
artifact paths and SHA-256
verifier command and full result
completion gates affected
supported claims and non-claims
remaining blockers
manual integration steps
```

Send the integration owner a short block:

```text
branch:
commit:
tests:
artifact:
artifact SHA-256:
verifier result:
limitations:
```

## 9. Integration checklist

- [ ] Correct ownership and base commit.
- [ ] No contract or previous-result mutation.
- [ ] No protected-split leakage.
- [ ] No fake/default production output.
- [ ] No secrets, caches, weights, tensors or large archives in Git.
- [ ] Typed, documented public interfaces.
- [ ] Relevant and full tests pass.
- [ ] Evidence passes its declared verifier.
- [ ] Code behavior, tests, evidence and future work are distinguished.

## 10. Prompt for a fresh coding agent

> Continue the existing AETHER repository; do not start a new project. Read
> AGENTS.md, RESEARCH_CONTRACT.md, PROJECT_STATE.md, TASK.md,
> docs/team/COMPLETE_PROJECT_STUDY_GUIDE.md,
> docs/team/PHASE1_FINAL_SPRINT_MASTER.md and the assigned member brief fully
> before editing. Work only on the assigned owner branch and paths. Inspect and
> reuse current implementations; do not create a third competing runner. Do not
> modify contracts, frozen methods, earlier evidence or protected splits. Do not
> fabricate results. Add fail-closed validation, atomic persistence and an
> independent verifier. Run relevant tests and provide commits, exact test
> counts, artifacts, hashes, limitations and manual actions.

