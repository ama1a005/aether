# AETHER Repository Audit

**Audit date:** 2026-10-11  
**Branch:** `main` at `8927181`  
**Mode:** single builder (temporary project rule)

## Repository state

- `main` tracks `origin/main`; no tracked-file modifications were present at audit start.
- Two untracked authoritative planning documents exist: `3_ProjectDescription.md` and `Phase1Project.md`. They have been preserved unchanged.
- `ProjectDescription.md` is not present under the exact filename requested by the project prompt; the apparent equivalent is `3_ProjectDescription.md`.
- The worktree also contains an inaccessible `.pytest_cache` entry that makes some Git/status commands emit a permission warning.
- Recent history: `8927181` integration smoke/docs, `5182400` P1/P2 modules, `500ee8b` P3/P4 modules.

## What exists

### Implemented

- Frozen v0.1.0 dataclass contracts for cases, messages, attacks, run traces, activation metadata, interventions, and circuit results.
- A deterministic rule-based two-agent target with mock MCP tools and structured A2A messages.
- Fifteen generated attack fixtures across tool-description, tool-output, and A2A-manipulation families.
- ASR/statistics helpers and an MCPTox-labelled adaptation layer.
- Generic PyTorch forward-hook capture, activation cache, zero/mean ablation, and activation patching primitives.
- Synthetic single-agent and cross-agent causal demonstrations, greedy and random search, graph serialization, and deterministic remediation selection.
- Unit, integration, and subprocess regression tests plus previously generated CSV/JSON/PNG artifacts.

### Partial or prototype-only

- The target agents are rule-based; there is no open-weight model wrapper or frozen model/tokenizer revision.
- Activation capture is generic PyTorch infrastructure only. It has not been integrated with the target pipeline or validated on a real transformer.
- The cross-agent graph is a lightweight dictionary graph. `load_from_activation_traces` creates nodes but no experimentally verified edges.
- Sender/message/receiver intervention demonstrations use synthetic callbacks and fixed thresholds, not logged model interventions.
- The benchmark registry contains several `TBD` pins/hashes and is YAML rather than the requested Phase 1 manifest JSON.
- Existing artifacts are smoke/demo evidence. They do not contain the complete reproducibility manifest required by `AGENTS.md` and the research contract.

### Not started

- BFCL competence evaluation, official-compatible MCPTox execution, TAMAS integration, and objective non-medical paired-task evaluation.
- Tracr calibration and canonical GPT-2 IOI/Greater-Than reproduction.
- Real paired clean/attacked sender and receiver activation traces.
- Experimental bridge verification on a real model, matched causal controls, beam search, and locked-test protocol.
- Paper-ready experiment manifests, environment lock, CI, Docker/environment image, notebooks, and paper pipeline.
- PTB-XL ingestion (the current loader intentionally raises `NotImplementedError`).

## Broken or unverifiable

- No Python executable (`python`, `py`, or `python3`) is available on PATH in the audited shell. Therefore no current test or smoke result could be reproduced on 2026-10-11.
- `instrumentation/trace_capture.py` annotates `Any` without importing it; importing that module is expected to fail when annotations are evaluated.
- `causal/bridge/intervention.py` imports `pandas`, but `pandas` is absent from `pyproject.toml`.
- Public interfaces generally lack the docstrings and type hints required by `AGENTS.md`.
- Root `PROJECT_STATE.md` and `TASK.md` describe the 8 October sprint and overstate present verification; their historical claims were not altered during this audit.

## Tests and results

- Recorded historical claim: 83 tests passed and 9/9 end-to-end checks passed on 2026-10-08.
- Audit attempt: `python -m pytest tests/unit/ tests/integration/ tests/regression/ -q`.
- Audit outcome: command did not start because `python` was not found.
- Existing result artifacts were preserved. Their numeric values must not be treated as independently revalidated by this audit.

## Repository hygiene and duplication

- `single_agent_circuit_smoke.py` and `end_to_end_smoke.py` contain separate toy-model implementations; this is limited demo duplication, not yet a production abstraction.
- There is no evidence of embedded model caches or credentials in the inventoried tracked files.
- No destructive cleanup was performed. No generated results were rewritten.

## Stage-0 verification update (2026-10-11)

- Verified interpreter: CPython 3.11.9 at `.venv/Scripts/python.exe`.
- The `py` launcher remains unavailable in the agent shell, but the user-supplied Python 3.11 interpreter created the existing local environment.
- PowerShell activation is blocked by execution policy; direct use of `.venv/Scripts/python.exe` is verified and isolates all installs.
- Corrected the invalid setuptools backend, declared pandas, and installed the project editable into `.venv`.
- Baseline: 83 passed; post-manifest suite: 84 passed. Both had one cache-permission warning.
- All five documented smoke commands passed independently.
- Added a resolved dependency lock, minimal Windows/Python 3.11 CI, and tested run-manifest infrastructure.
- No model or benchmark was downloaded.
- Current authoritative master candidate is `4_ProjectDescription.md`; no exact `ProjectDescription.md` exists. It matches the additive AETHER platform plus DCMG/BVP architecture.
- Manifest hardening increased the verified suite to 85 passing tests and requires explicit dataset identity/version/split/subsets plus artifact hashes and timing fields.

