# AETHER Complete Project Study Guide

## The project in one page

AETHER is a research system for studying adversarial failure and causal information flow in a tool-using, two-agent pipeline. A synthetic `CaseRecord` is converted into tool evidence. A sender produces a structured `MediatorMessage`; a receiver converts that message into an outcome. An `AttackDelta` changes a narrowly authorized field, while instrumentation and interventions ask where the resulting behavior is represented and transmitted.

The repository separates four questions. The target harness in `target/` asks whether the protocol executes reproducibly. The attack layer in `attacks/` asks whether an allowed perturbation changes behavior. The mechanistic layer in `mechanistic/` and `interventions/` asks which internal components are causally important. The cross-agent layer in `causal/` asks whether sender state, the explicit message bridge, receiver state, and outcome form a recoverable causal path.

The central evidence discipline is: **implementation is not a result; a passing test is not validation; development evidence is not held-out evidence; and a blocked experiment supports no success claim.** `RESEARCH_CONTRACT.md` freezes novelty and metric meanings. `AGENTS.md` freezes operational rules. Run manifests tie every executed claim to code, data, model revision, seed, hardware, environment, command, and raw output.

## Motivation, original idea, and corrected novelty

The original ambition combined an agent-security evaluation platform, mechanistic circuit discovery, cross-agent causal tracing, and remediation. Mentor feedback and prior-art review required a narrower claim: building all of those capabilities is engineering breadth, not automatically research novelty. AETHER therefore treats the platform as the measurement instrument. The defensible research question is whether adversarial behavior in a paired tool-using agent protocol can be localized across sender internals, a structured message bridge, receiver internals, and outcome, then causally tested with aligned interventions. The novelty claim is the cross-agent causal object and evaluation protocol—not MCP itself, ordinary prompt injection testing, generic activation patching, or a dashboard.

Platform capability means what the repository can execute. Research novelty means the new, falsifiable scientific contribution supported by evidence. Demo capability means what can be explained reliably in a review. A feature may belong to the first and third categories without yet supporting the second.

## End-to-end data flow

1. `target.case_loader` supplies a versioned synthetic case.
2. `target.mcp.tools` converts fields into deterministic tool evidence.
3. The sender produces `contracts.MediatorMessage`, including a recommendation code and provenance.
4. `attacks` constructs and validates an `AttackDelta`; the review attack changes only the permitted recommendation field.
5. The receiver maps the message to a final decision.
6. `mechanistic` hooks capture selected model activations without changing logits; `interventions` ablate or patch specified components.
7. `causal.candidate_graph` represents sender, message, receiver, and outcome nodes; mediation code measures how much clean behavior is restored by a patch.
8. Experiment runners write raw output and reproducibility metadata. Summary documents point to those artifacts rather than replacing them.

## Metrics and interpretation

- **Attack success rate (ASR):** fraction of eligible clean-correct examples for which the attack produces the defined target failure. Always state the denominator and eligibility rule.
- **Clean utility:** performance on unperturbed cases. An attack result without clean utility can conceal a broken target.
- **Faithfulness:** how well a selected component set reproduces the defined causal effect relative to the full reference intervention. It is not ordinary prediction accuracy.
- **Normalized mediation recovery:** the fraction of the clean-to-attacked outcome gap restored by an intervention. The sign, denominator, zero-gap behavior, and outcome scale are fixed by the research contract.
- **Random baseline percentile:** contextualizes selected circuits against size-matched random sets; it does not create held-out validation.

## Protocol evolution and experimental design

Early synthetic and fixture runs established interfaces but could not support real-model claims. Real-model instrumentation then established that the adapter/hook path could execute on the small Qwen line. Paired clean/attack traces created aligned mediator and receiver observations. The standardized attack anchor restricted the manipulated semantic field so that later causal effects would be interpretable. Development localization and balanced V2 work addressed class imbalance and trivial signal concerns. Generation-step interventions and head instrumentation moved from coarse module observations toward token- and head-specific hypotheses. Model qualification now acts as a gate: a candidate model must satisfy loading, correctness, memory, and intervention-readiness criteria before expensive discovery proceeds.

MCPTox and TAMAS are relevant external evaluation lines, while BFCL, AgentDojo, Tracr, and NARCBench represent possible later comparisons or tasks. They are not current evidence and must not be downloaded or run merely for the review. Phase 1 targets a reproducible paired causal result on the bounded protocol; Phase 2 expands tasks, models, attacks, remediation choices, and validation only after the Phase-1 gate.

## Intervention and remediation space

Sender intervention changes selected sender activations before message generation. Message intervention replaces a field or the whole structured mediator. Receiver intervention changes receiver activations after message ingestion. Generation-step intervention specifies when a patch occurs rather than treating an entire sequence as one location. Remediation candidates may operate at any of these points, but selection must balance attack reduction, clean-utility cost, complexity, and robustness. A Pareto frontier retains candidates not dominated on all objectives; it does not collapse the trade-off into an arbitrary single score.

## Results map: positive, negative, and unknown

Completed software evidence includes frozen contracts, deterministic MCP-style tools, attack storage/evaluation, non-interference and intervention primitives, synthetic known-path recovery, paired traces, message rescue, manifests, and smoke tests. Development artifacts support bounded statements on the exact configurations recorded in them. Important negative/null evidence includes localization/configurations that did not generalize cleanly and the MQ-HW1 larger-model attempt blocked at host-memory readiness. These outcomes are scientifically useful because they restrict model and architecture claims.

What is currently proven is that the implemented bounded paths execute, synthetic known paths can be tested, and a clean mediator can restore the designed attacked outcome in aligned review cases. What is not proven includes clinical correctness, external benchmark superiority, held-out circuit generalization, causal completeness of the candidate graph, effectiveness on arbitrary multi-agent systems, and readiness of Qwen2.5-1.5B for this workstation.

## Phase targets and schedule logic

The final Phase-1 target is one fully reproducible, qualified-model, paired clean/attack causal analysis with frozen metrics, honest negative results, and an untouched confirmation split. Phase 2 through April is conditional: broaden attack families and benchmarks, compare models, evaluate sender/message/receiver remediation candidates, test Pareto trade-offs, and package the strongest supported result. Every expansion requires a bounded `TASK.md`; none is implied by the review demo.

## Evidence ladder

1. Unit tests: local software behavior.
2. Integration/smoke tests: interfaces compose and artifacts are produced.
3. Synthetic known-path experiments: recovery of an injected causal structure.
4. Real-model development experiments: empirical evidence used for design and calibration.
5. Qualification gates: bounded checks that decide whether a model/configuration may advance.
6. Held-out validation and external benchmarks: future evidence only after prerequisites pass.

The review demo spans levels 1–3 live and displays previously committed higher-level artifacts with their original labels. It must not blur these categories.

## Current state

The Stage-0 environment, contracts, target harness, attack framework, hook/intervention primitives, cross-agent graph, and paired message-rescue foundation exist. The intermediate review demo uses twelve synthetic cases and real core interfaces. The reliable default path is deterministic and labels itself accordingly. Qwen2.5-0.5B is the small review-model line; the Qwen2.5-1.5B MQ-HW1 qualification remains blocked by local host-memory constraints and has not earned progression. No external benchmark download or validation run should begin merely to improve the presentation.

## Architecture invariants to memorize

- Contracts cannot change without a schema issue and teammate approval.
- Core modules never import `demo`; dependency direction is `demo -> core`.
- Production experiment errors are explicit; there are no silent fallbacks.
- Raw outputs and manifests are required for quantitative claims.
- Synthetic/replay/model-free paths are visibly labelled.
- Member ownership is defined in `docs/team/team_ownership.yaml`.

## Oral-review preparation

Be able to trace one clean case, one attacked case, and one rescued case field by field. Be able to name one negative or blocked result and explain why preserving it improves the research. Be able to distinguish a mediator-message intervention from an internal activation patch. Finally, be able to state the next decision gate without promising its outcome.

## Reading order

1. `RESEARCH_CONTRACT.md`
2. `PROJECT_STATE.md` and `TASK.md`
3. `contracts/`
4. `target/`, then `attacks/`
5. `mechanistic/` and `interventions/`
6. `causal/`
7. `results/` manifests and summaries
8. `docs/INTERMEDIATE_REVIEW_RUNBOOK.md` and the member guide matching your ownership

