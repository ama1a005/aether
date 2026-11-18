# Member 4: CORE-03, locked evaluation and final report

**Branch:** `m4/cross-agent-graph`
**Deadline:** 20 November 2026, 15:00 Asia/Kolkata

## Mission and boundaries

Complete the central causal sequence without leakage: CORE-03, locked
validation, once-only test, statistics, final evidence report and integration.
Only this track may control protected-split access.

## Step 1: verify and ingest CORE-03

Relevant paths:

```text
experiments/phase1/core03_remediation.py
instrumentation/core03_evaluator.py
scripts/verify_core03_remediation_bundle.py
scripts/ingest_core03_remediation_bundle.py
notebooks/aether_qwen_core03_remediation.ipynb
```

When the archive arrives:

1. compute archive SHA-256 before extraction;
2. safely extract to new staging; reject absolute/parent paths, links and
   multiple roots;
3. run the independent verifier without editing artifacts;
4. require 15 arm/seed units, 120 rows, <=624 forwards, zero validation/test,
   pinned model/source/proposal and clean source;
5. verify every inventory hash;
6. ingest atomically into `results/phase1/remediation`, refusing overwrite;
7. record archive hash and receipt;
8. derive conclusions only from verified machine-readable artifacts;
9. retain `COMPLETE_NO_FEASIBLE_REPAIR` if produced;
10. retain the paired-clean-donor/oracle limitation.

## Step 2: freeze locked validation

Only after CORE-03 verification, create a versioned proposal freezing:

- exactly the selected CORE-03 arm, without reselection;
- model/tokenizer revisions;
- validation case IDs and manifest hash without reading outcomes;
- prompt/message schema versions;
- intervention and donor semantics;
- security and clean-utility endpoints;
- eligibility/denominators and invalid/error handling;
- unchanged development-derived thresholds;
- seeds/generation parameters;
- budgets;
- statistics/confidence intervals;
- checkpoint/resume behavior;
- artifacts/schemas/failure states;
- test execution locked to zero;
- prohibition on validation tuning;
- exact human review requirement.

Add fail-closed tests for hash drift, selected-arm identity, case isolation,
budget, units, denominators, approval and incomplete runs. Publish the exact
SHA-256 and stop for human approval.

## Step 3: implement and execute validation

After approval:

1. implement a commit-pinned notebook using the approved device/dtype;
2. fail before model access unless preflight passes;
3. checkpoint the smallest safe unit to durable storage;
4. prevent validation output from changing the method;
5. retain every raw row/error;
6. implement an independent verifier;
7. verify coverage, budget, split counts, hashes and arm identity;
8. atomically ingest into `results/phase1/validation`;
9. report pass/fail under frozen criteria without adaptation.

## Step 4: freeze and run the once-only test

Only after validation ingestion/review:

1. freeze final model, repair, thresholds, prompts and code;
2. freeze test manifest and once-only attempt ID before access;
3. distinguish infrastructure failure from scientific failure;
4. require exact human approval;
5. durably record `attempt_started` before test access;
6. execute exactly once and preserve every output/error;
7. derive summary only from raw rows;
8. independently verify once-only marker, coverage, method identity and hashes;
9. atomically ingest into `results/phase1/test` without overwrite;
10. never reopen test for tuning.

## Step 5: final statistics and report

Generate only from independently verified ingested evidence. Include exact
cohort sizes/denominators, attack and clean endpoints, confidence intervals,
declared paired tests, seed stability, invalid/error counts, controls,
ablations, CORE-02 cost comparison, CORE-03 outcome, validation/test,
calibrations, benchmarks/supporting evidence, QCI-1 negative result,
decision-code-copying limitation, oracle-donor limitation and blocked work.

The report generator must reject unverified/incomplete/schema-incompatible
inputs. No manual number transcription into machine-readable results.

## Step 6: integrate teammate work

For each branch:

1. inspect diff and ownership;
2. verify no contract/result/protected-split mutation;
3. run relevant tests;
4. independently verify evidence;
5. integrate code before evidence where practical;
6. resolve conflicts in favor of frozen contracts and current verified data;
7. run full Python/frontend/smoke suites;
8. regenerate completion and execution status;
9. update project state, task, study guide and manual actions.

Final commands:

```bash
python -m pytest tests/unit -v
python -m pytest tests/integration -v
python -m pytest tests/regression -v
python -m experiments.phase1.single_agent_circuit_smoke
python -m experiments.phase1.cross_agent_smoke
python scripts/smoke_test.py
python scripts/phase1_execution_status.py
cd demo/frontend
npm ci
npm test -- --run
npm run build
```

## Definition of done

- CORE-03 verifies and is ingested.
- Validation protocol predates access and verified validation is ingested.
- Test protocol predates access and the once-only attempt verifies.
- Final report consumes only verified evidence.
- Missing external work remains visibly blocked, never disguised.
- All integrated tests, smokes and demo build pass.
- Final Git checkpoint is clean except preserved user-owned local files.

