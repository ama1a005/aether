# Markdown authority and currency index

**Current as of:** 21 November 2026

The repository contains design documents, current status documents, frozen
protocols, runbooks, historical checkpoints and generated evidence notes. “Up
to date” does not mean rewriting every historical file: changing a frozen
proposal or old execution record would destroy the audit trail. Use the classes
below to decide which document controls a statement.

## Current authoritative documents

| Question | Controlling document |
|---|---|
| What is AETHER's frozen novelty and metric contract? | `RESEARCH_CONTRACT.md` |
| What has actually executed? | `PROJECT_STATE.md` and retained result artifacts |
| What should be said in the review? | `docs/PRESENTATION_EVIDENCE_GUIDE.md` |
| Where did every active demo/experimental case come from? | `docs/DATASET_AND_CASE_PROVENANCE.md` |
| What is the active demo and how is it run? | `DEMO_README.md` |
| What is demo versus scientific evidence? | `docs/DEMO_SCIENCE_BOUNDARY.md` |
| What remains executable or blocked? | `docs/PHASE1_EXECUTION_AND_EVIDENCE_GUIDE.md` and `TASK.md` |
| What manual action is required? | `docs/MANUAL_ACTIONS.md` |
| What was run, including negative results? | `docs/EXPERIMENT_LEDGER.md` |

## Current presentation data statement

The active demo uses twelve exact PTB-XL v1.0.3 records selected only from
folds 1–8. Source URLs, file hashes, record IDs, license and derivation rules are
in `demo/cases/ptbxl_source_manifest.json`. `ESCALATE`/`DO_NOT_ESCALATE` is an
AETHER-derived demonstration mapping, not an official PTB-XL or clinical label.
The old `demo/cases/demo_cases.json` file is retained as historical synthetic v1
input and is no longer the active case registry.

## Historical but intentionally immutable documents

These files remain valid records of what was planned, approved or known at a
specific time. Their old “pending” language is not a current status claim:

- `configs/phase1_core/*freeze*` and their human-review Markdown files;
- protocol approvals and proposal reviews;
- `docs/checkpoints/`, `docs/handoffs/` and sprint handoff notes;
- archived notebook run instructions tied to immutable commits;
- old status sections explicitly marked historical or superseded;
- the original synthetic demo registry and replay directory.

Never edit those records merely to make their dates or future-work statements
look current. Add a dated addendum to a current authority document instead.

## Runbooks and preparation documents

Benchmark runbooks describe how an experiment should execute. They do not prove
that it executed. In particular, BFCL, MCPTox, TAMAS and AgentDojo preparation
must not be converted into official result claims without an accepted bundle
from the declared verifier.

## Conflict rule

If documents disagree, use this order:

1. `RESEARCH_CONTRACT.md`;
2. independently verified raw/result artifacts;
3. root `PROJECT_STATE.md`;
4. the two current presentation/provenance guides;
5. current code and tests;
6. planning documents and historical notes.
