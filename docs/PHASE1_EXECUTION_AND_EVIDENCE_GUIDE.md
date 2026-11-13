# Phase-1 execution and evidence guide

Version: 1.0 (2026-11-14)  
Scope: Phase 1 only  
Authority: `RESEARCH_CONTRACT.md` and frozen protocol artifacts override this guide.

## What “finished” means

Phase 1 is complete only when `python -m scripts.audit_phase1_completion`
returns `PASS`. A working implementation, a unit test, a synthetic smoke run,
an adapter, or a prepared notebook is not experimental evidence. The status UI
and `python -m scripts.phase1_execution_status` preserve that distinction.

The repository currently has verified Qwen qualification, instrumentation,
development capture, QCI/QCI-2 development evidence, method-freeze approval,
and Tracr/IOI calibration. CORE-02 matched search is the active external run.
No validation or test split may be opened until the frozen dependency chain
authorizes it.

## Four evidence levels

1. **Implemented**: production code exists and fails explicitly.
2. **Tested**: model-independent unit/integration tests passed.
3. **Executed**: a declared experiment ran and retained raw artifacts.
4. **Verified evidence**: the artifact-specific verifier and completion gate pass.

Only level 4 contributes to Phase-1 completion.

## Machine-verifiable control plane

- Frozen evidence requirements: `configs/phase1_completion_gates.yaml`
- Prospective execution dependencies: `configs/phase1_execution_registry.yaml`
- Evidence audit: `python -m scripts.audit_phase1_completion`
- Readiness report: `python -m scripts.phase1_execution_status`
- Review UI endpoint: `GET /api/demo/phase1-status`
- Review UI page: **PHASE-1 EVIDENCE**

The execution registry must exactly cover all evidence gates. Its validator
rejects missing/extra stages, cycles, unknown dependencies, unsafe paths, and
nonexistent declared runners.

## Remaining sequence

| Order | Gate | Current action | Promotion rule |
|---:|---|---|---|
| 1 | matched search | Resume `notebooks/aether_qwen_core02_matched_search.ipynb` from the retained checkpoint | Verify with `scripts/verify_qci2_matched_search_bundle.py`, then ingest with `scripts/ingest_qci2_matched_search_bundle.py` |
| 2 | remediation | Freeze the result-dependent intervention only after CORE-02 verification | New raw model run plus declared summary predicates |
| 3 | locked validation | Human authorization after method/remediation freeze | Protocol frozen before access; test executions remain zero |
| 4 | once-only test | Run exactly once only after validation decision | `method_frozen=true`, `once_only=true` |
| 5 | official/supporting evidence | Run independent external protocols; never translate smoke outputs into official scores | Each declared summary and provenance verifier passes |
| 6 | final report | Generate from verified manifests only | Incomplete inputs are rejected |

CORE-02 can be resumed across Kaggle sessions. A partial checkpoint archive is
not final evidence and must not be ingested as a completed search.

## Official datasets and benchmarks

### BFCL

`configs/benchmarks/phase1_external.yaml` pins `bfcl_eval` 2026.3.23, its wheel
hash, the immutable Qwen revision, complete categories, and the disclosed AETHER
Qwen2.5 adapter. `benchmarks/native_runners.py` constructs the official generate
and evaluate commands. `benchmarks/bfcl_qwen25.py` verifies every model snapshot
file before delegating to the official evaluator. This is executable on the GPU
host, but the resulting official artifact has not yet been produced.

### MCPTox

The source commit and dataset hashes are pinned in `docs/MCPTox_INTEGRATION.md`.
The released repository has no license file and does not provide the evaluator
needed to reproduce an official score. The checked-in result is released-response
rescoring only. It is scientifically invalid to relabel it as an official local
Qwen execution. Human license review and an author-provided/reproducible official
protocol are required.

### TAMAS

The source, commit, licenses and 300-case identity are pinned in
`docs/TAMAS_INTEGRATION.md`. Native execution targets AutoGen/CrewAI and can
require provider credentials and LLM-based assessment. Running those cases in
the AETHER two-agent harness would be a transformed benchmark, not an official
TAMAS score. Native framework execution must remain separately labelled.

### AgentDojo

The package, benchmark version, suite and explicit task IDs are pinned in
`configs/benchmarks/phase1_external.yaml`; `benchmarks/native_runners.py` creates
the official CLI plan. It is prepared supporting evidence, not one of the 22
frozen completion gates.

## Test-case basis

- The review frontend uses 12 synthetic, development-only cases declared in
  `demo/cases/demo_case_manifest.json`; they are demonstration fixtures, not a
  clinical dataset and not validation/test evidence.
- Qwen development experiments use the frozen split registries and retain zero
  validation/test executions until authorized.
- Benchmark adapters retain official case identifiers and invalid/error rows;
  they do not silently drop failures.
- Calibration uses known-structure Tracr and GPT-2 IOI controls to verify that
  the intervention machinery can recover known behavior before AETHER claims.

## Frontend execution

Start the demo with `scripts/run_review_demo.ps1`. The UI exposes:

- case and FHIR MCP workspace;
- clean, attack, rescue and induction execution;
- raw MCP request/response provenance;
- verified replay when live dependencies are unavailable;
- a live repository evidence/readiness page.

Replay, deterministic execution and real MCP execution are visibly distinct.
There is no silent fallback from a failing live service to mock data. The UI is
research demonstration software and is not clinical decision support.

## Manual actions that cannot be automated honestly

1. Keep resuming CORE-02 until the final archive exists; upload each checkpoint
   privately to the next Kaggle session.
2. Return the final archive for local verification and ingestion.
3. Approve the remediation/locked-split protocol only after its prospective
   proposal and hashes are reviewed.
4. Supply any benchmark credentials under the official framework; never commit
   tokens or model caches.
5. Obtain MCPTox licensing/protocol clarification before claiming a new official
   result.
6. Select and pin a scientifically suitable trained SAE checkpoint and second
   model before those runs. Absence of a suitable artifact is a real limitation,
   not something a mock checkpoint can repair.

## Daily verification commands

```powershell
.\.venv\Scripts\python.exe -m scripts.phase1_execution_status
.\.venv\Scripts\python.exe -m pytest tests/unit -q
.\.venv\Scripts\python.exe -m pytest tests/integration -q
.\.venv\Scripts\python.exe -m pytest tests/regression -q
```

Run `python -m scripts.audit_phase1_completion` last. Its nonzero exit while
evidence is missing is expected and must not be bypassed.

## Prepared external execution packages

The following packages are implemented and model-independent tested:

- `benchmarks.run_native_official`: pinned BFCL/AgentDojo native commands,
  clean-source enforcement, raw command logs and official-output retention.
- `experiments.phase1.qwen_red_team`: literal description/output/message attacks
  through a real Qwen sender and receiver under a bounded campaign ledger.
- `experiments.phase1.qwen_agent_c`: deterministic Agent-C clean-tool review of
  the retained real-Qwen A/B traces; it is explicitly not a third Qwen model.
- `experiments.phase1.qwen_sae_evaluation`: checkpoint/model/component identity,
  tensor safety, reconstruction threshold and per-case sparsity evaluation.
- `paired_trace.run_secondary_model_qualification`: reuse of the complete
  MQ-HW1/G1/G2 engine for a distinct, reviewed immutable model candidate.
- `experiments.external_bundle`: exact artifact inventory, split-lock checking,
  independent verification and no-overwrite atomic ingestion.
- `evaluation.phase1_evidence_report`: refuses final output until every
  non-report evidence gate is PASS or NOT_APPLICABLE.
- Official and supporting Kaggle notebook builders under `scripts/build_kaggle_*`.

The red-team, Agent-C and SAE configs intentionally remain at human-review
gates. Their current SHA-256 values are respectively
`dc1204374fd7e2207a7af694ff173e4ca781807bb9f2bb4ba6ba9fecb98ced03`,
`94e724ce189d9247da79436bfed36de34a3d431112b77a6c3bdacb939a942a5c`, and
`d26478bbd31d820e2068ba37cbd8c361df89024caecf5a8db1e998eaf61c94e5`.
Approval must be recorded prospectively before changing each status to
`frozen_and_human_approved`. Selecting a trained SAE or second model remains a
scientific choice, not a code default.
