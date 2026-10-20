# Member 1 — Target and Protocol Guide

## A. Full project context

AETHER uses a paired sender/message/receiver protocol as an instrument for measuring adversarial propagation and causal recovery. Its defensible novelty is the tested cross-agent causal path, not the existence of agents, MCP tools, or a UI. The target, attack, instrumentation, and causal modules are implemented; real-model qualification and held-out validation remain bounded future gates.

## B. Member responsibility

Member 1 owns the executable boundary from synthetic case to sender message and receiver outcome. Study `target/case_loader.py`, `target/mcp/tools.py`, `target/runner.py`, and the frozen types in `contracts/`. The key responsibility is reproducibility: the same inputs and configuration must yield an auditable trace, with failures exposed rather than replaced by plausible defaults.

For the review path, understand FHIR resources, HAPI FHIR R4, WSO2 FHIR MCP, Streamable HTTP tool discovery, generic `read`/`search`, and the AETHER FHIR adapter. The frontend never calls FHIR directly.

Inputs are validated cases/configuration/model settings; outputs are tool events, `MediatorMessage`, receiver decision, `RunTrace`, and manifest-linked raw output. Member 1 depends on frozen contracts and hands aligned traces to M2–M4.

## C. Code map and D. execution flow

Begin at `target/runner.py`; follow case loading through `target/case_loader.py`, tool calls in `target/mcp/tools.py`, orchestration, message serialization, receiver parsing, and artifact writing. Keep `contracts/` read-only unless the formal schema process is followed. Relevant tests live under `tests/unit/` and `tests/integration/`; experiment YAML belongs under `configs/experiments/`.

## E. Important algorithms, F. data models, and G. configs

The important operations are deterministic case selection, prompt/tool assembly, structured-message parsing, receiver decision mapping, and stable trace serialization. The key models are `CaseRecord`, `ToolCall`, `ToolResult`, `MediatorMessage`, and `RunTrace`. Configuration must identify dataset, prompts, model/tokenizer revisions, generation settings, seeds, and artifact locations without hard-coded user paths.

## H. Tests, I. experiments, and J. current negative results

Unit tests check schema/tool/parser behavior; integration and smoke tests check the full chain. Fixture successes prove plumbing only. Real-model experiments require their manifests. Current limitations include synthetic cases, bounded actions, and the fact that MQ-HW1 did not clear host-memory readiness.

## K. Demo responsibility and L. code review preparation

Show `DEMO-PAT-001` from case through tools to mediator and receiver. Keep `target/runner.py`, `target/mcp/tools.py`, the relevant contracts, and a run manifest open. Explain why deterministic review execution is labelled model-free and where a qualified model later plugs in.

## M–N. Thirty likely questions with answers

1. **What is the target system?** A two-agent, tool-using protocol whose sender emits a structured mediator message and whose receiver emits the final decision.
2. **Why use contracts?** They make boundaries machine-checkable and prevent modules from silently disagreeing about fields or types.
3. **Can you rename a contract field?** No; `AGENTS.md` requires a schema-change issue and one teammate approval.
4. **What begins a run?** A versioned synthetic case plus deterministic configuration, model revision, seed, and prompt versions.
5. **Why are tools separate from agents?** Tool evidence can be tested independently and its provenance can be logged.
6. **What does `target/mcp/tools.py` provide?** Deterministic transformations for evidence such as ECG, vitals, and history used by the harness and demo.
7. **What is a mediator message?** The explicit structured bridge carrying the sender’s recommendation and supporting context to the receiver.
8. **Why is that bridge important?** It is both an operational interface and a causal intervention point.
9. **What does the receiver consume?** The frozen mediator schema, not arbitrary hidden sender state.
10. **What is clean utility?** Performance on unperturbed eligible cases; it verifies the target works before attack effects are interpreted.
11. **Why exclude clean-incorrect cases from some ASR denominators?** An attack cannot meaningfully cause a failure that already existed; the research contract fixes eligibility.
12. **What must a trace contain?** Inputs, tool calls/results, messages, outputs, identifiers, timing/provenance, and required manifest linkage.
13. **Why record raw output?** Summaries cannot reconstruct unexpected behavior or support later audit.
14. **What is a hidden fallback?** Catching a failure and returning a normal-looking default; it is prohibited because it corrupts evidence.
15. **Are demo cases patient data?** No. `demo/cases/demo_cases.json` is explicitly synthetic and educational.
16. **Does a clinically plausible case establish medical correctness?** No; plausibility is presentation scaffolding, not clinical validation.
17. **What is the default review path?** Deterministic orchestration of real AETHER interfaces, visibly labelled as model-free for that run.
18. **Why is determinism useful in review?** It makes control flow inspectable and avoids intermittent model/resource failures while preserving scientific labels.
19. **Where is model identity recorded?** In the experiment manifest, including model and tokenizer revisions.
20. **Why pin revisions?** A model name alone can resolve to different weights or tokenizer behavior later.
21. **What does a smoke test establish?** That a bounded path composes and produces expected artifact structure, not external validity.
22. **How do you debug a wrong receiver outcome?** Inspect case, tool evidence, sender message, attack delta, receiver mapping, and manifest in that order.
23. **What should never be logged?** Credentials, private patient data, or unbounded model caches/tensors in git.
24. **Who consumes Member 1 output?** Member 2 evaluates attacks, Member 3 captures activations, and Member 4 builds the mediation graph.
25. **What is the most fragile interface?** The structured mediator message because changes affect attacks, receiver behavior, and causal intervention semantics.
26. **How is a run made reproducible?** Log commit/diff state, data hashes, revisions, seeds, hardware, environment hash, command, config, and raw-output path.
27. **What if a tool errors?** Surface a clear error and preserve diagnostics; do not synthesize evidence.
28. **Why must core not import demo?** It keeps the review layer removable and prevents presentation concerns from altering research behavior.
29. **What should Member 1 show live?** One clean trace from case through tools and message to receiver, with schema and provenance visible.
30. **What remains after the demo?** Qualify the intended model under the defined hardware gate before expanding experiments.

## Handoff checklist

Confirm that cases validate, tools are deterministic, sender and receiver payloads match frozen contracts, traces contain reproducibility fields, and consumers receive stable artifact paths. Ask M2 to review attack eligibility, M3 to review capture points, and M4 to review mediator semantics.

## O. Cross-member questions

Know how M2 defines an eligible attack, why M3 requires hook non-interference, and why M4 distinguishes message mediation from internal circuit localization. The target trace is the shared coordinate system for all three.

## P. Glossary and Q. command cheat sheet

`MCP`: tool/context protocol boundary. `Mediator`: structured sender-to-receiver variable. `Clean utility`: unperturbed target performance. Run `python -m pytest tests/unit/ -v`, `python -m pytest tests/integration/ -v`, and the configured `python -m target.runner ...` command.

## R. Debugging, S. limitations, and T. future work

On failure, inspect schema validation, tool inputs, rendered prompt, raw sender output, parser error, receiver input, then artifact write. Do not catch and default. Current scope is synthetic and binary; future work is conditional on qualified-model execution and untouched confirmation data.

