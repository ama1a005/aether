# AETHER Intermediate Review Runbook

## External FHIR MCP startup

Run `scripts/start_review_fhir_stack.ps1`, then `scripts/run_review_demo.ps1 -Mode real_fhir_mcp_deterministic`. Confirm the FHIR MCP Data page names WSO2, Streamable HTTP, and local HAPI R4. Discover MCP Tools must show server-returned schemas. If MCP fails, state it and explicitly select mock or replay; real mode never falls back.

## Choose and state the execution mode

For a reliable presentation use `scripts/run_review_demo.ps1 -Mode deterministic`. For real execution, complete the setup and qualification in `DEMO_README.md`, then use `-Mode live_model_mcp`. Never describe deterministic fallback or replay as live Qwen/MCP. Live startup preloads the model and fails before serving if CUDA or the pinned local model is unavailable.

## Purpose and scientific boundary

This runbook presents a reliable code-review demonstration without changing the research protocol. The clinical-like records are synthetic and educational, not medical advice. The default live path is a deterministic orchestration of real AETHER contracts, tools, attack validation, and causal message-patching code. It is not presented as a fresh language-model experiment. Committed research cards are labelled by evidence tier and retain their original limitations.

## Before the room

1. From the repository root activate `.venv` and run `python -m pytest tests/unit/test_review_demo.py -q`.
2. Build the client with `cd demo/frontend` followed by `npm.cmd run build`.
3. Run `python -m demo.backend.generate_replays` only if demo behavior intentionally changed; inspect the diff rather than accepting new numeric claims blindly.
4. Start with `powershell -ExecutionPolicy Bypass -File scripts/run_review_demo.ps1`.
5. Confirm `/api/health` reports healthy, the header says `Synthetic / Educational`, and twelve cases appear.
6. Keep `DEMO-PAT-001` selected for the main path and `DEMO-PAT-002` ready as the benign comparison.

## Seven-minute presentation

1. **Problem (45 seconds).** AETHER asks where an adversarially influenced recommendation propagates across a tool-using, two-agent pipeline and whether a targeted intervention restores the clean outcome.
2. **Architecture (45 seconds).** Show Tools, then Pipeline. The sender consumes synthetic evidence and emits a frozen `MediatorMessage`; the receiver maps its recommendation code to the final decision.
3. **Clean run (60 seconds).** Select `DEMO-PAT-001`, run Clean Pipeline, and point to `ESCALATE`, the tool trace, and structured message. Say explicitly that the review-safe path is deterministic core execution.
4. **Attack (60 seconds).** Run Attack. Show the before/after diff: only `recommendation_code` changes. Explain that `validate_attack_delta` enforces this bounded perturbation.
5. **Message rescue (60 seconds).** Run Rescue. Explain that the clean mediator message is patched into the attacked trajectory using the actual cross-agent intervention runner. The outcome returns to clean and normalized recovery is 1 for this designed demonstration pair.
6. **Mechanistic evidence (60 seconds).** Open Evidence. Separate validated development evidence from the failed/blocked qualification runs. Never describe a development localization as held-out validation.
7. **Status and next work (45 seconds).** Open Status. State that Qwen2.5-0.5B is the review model, Qwen2.5-1.5B MQ-HW1 remains blocked by host memory, and external benchmark/model expansion is intentionally deferred.

## Backup paths

- If a live request fails, switch to Replay mode and load the committed replay for the same case. State that this is a recorded execution artifact.
- If the browser does not start, open `http://127.0.0.1:5173` manually.
- If port 8000 or 5173 is occupied, stop only the process known to belong to this demo; do not kill unrelated Python or Node processes.
- If the model preload cannot fit, continue with the deterministic core path. Do not claim that a model ran.

## Claims reviewers may safely hear

- The software contracts, deterministic tools, attack validator, and message-patch intervention execute end to end.
- The demo corpus contains exactly twelve versioned synthetic cases.
- A one-field message attack can flip the receiver decision in designated demonstrations, and restoring the clean message restores the clean outcome.
- Existing evidence cards are summaries of committed executed artifacts, not newly generated results.

## Claims that are not permitted

- Clinical efficacy, diagnostic correctness, safety certification, or real-patient validity.
- Held-out validation, generalization, or benchmark superiority.
- Successful Qwen2.5-1.5B qualification while MQ-HW1 is blocked.
- Any number that cannot be traced to an immutable run artifact and reproducibility metadata.

## Likely questions

**Why deterministic?** Review reliability and scientific honesty. The path exercises production interfaces without disguising a model-free run as model evidence.

**Is rescue proof of mechanism?** It is causal evidence at the mediator-message level for the paired trajectory. It does not by itself localize an internal neural circuit or establish external validity.

**Why synthetic clinical cases?** They make the protocol legible while avoiding patient data and clinical claims.

**What failed?** The larger-model qualification did not clear the local-memory gate. That failure is preserved rather than hidden.

**What is next?** Obtain sufficient verified memory/headroom or suitable compute, rerun the bounded MQ-HW1 qualification, then proceed only if its decision gate passes.

## After the review

Stop the two processes opened by the launcher. Keep generated runtime files under `demo/artifacts/runs/` out of version control. Record any code-changing reviewer decision in `docs/RESEARCH_DECISIONS.md`; do not edit historical experiment output.
