# Member 2 — Attack and Evaluation Guide

## A. Full project context

AETHER studies whether bounded adversarial influence travels through a sender, structured message, receiver, and outcome, and whether interventions recover clean behavior. The attack subsystem supplies controlled contrasts; it is necessary infrastructure, while novelty rests in cross-agent causal testing.

## B. Member responsibility

Member 2 owns attack definitions, corpus provenance, eligibility, and metrics. Study `attacks/`, `data/attack_cases/`, `benchmarks/REGISTRY.yaml`, and the metric definitions in `RESEARCH_CONTRACT.md`. An attack result is meaningful only relative to a functioning clean target and an explicit threat model.

Inputs are clean cases/traces and versioned transformations; outputs are validated `AttackDelta` records, paired traces, per-example outcomes, ASR/clean-utility summaries, uncertainty, and provenance.

## C–G. Code, flow, algorithms, models, and config

Trace corpus loading and validation under `attacks/`, inspect the JSON cases in `data/attack_cases/`, and follow evaluator calls into metric aggregation. Important algorithms are eligibility filtering, targeted success classification, stratification, and bootstrap intervals. Key models are attack record, delta, target output, and evaluation row. Config must freeze corpus hash, family filters, prompts, target revision, seeds, bootstrap settings, and output paths.

## H–J. Tests, experiments, and negative results

Tests must reject malformed or over-broad deltas, verify denominators, and make seeded intervals repeatable. Fixture/mock ASR is plumbing evidence. A 100% mock result is not evidence of model vulnerability; failed and no-effect attacks remain in raw results.

## K–L. Demo and code review preparation

Show the exact clean/attacked JSON diff and the validator. Have `attacks/`, `data/attack_cases/atk_a2a_manipu_002.json`, metric tests, and a manifest ready. State the synthetic threat model before showing the outcome.

## M–N. Thirty likely questions with answers

1. **What is an attack case?** A versioned input plus a bounded transformation and expected evaluation conditions.
2. **What is an `AttackDelta`?** The structured record of authorized changes between clean and attacked trajectories.
3. **Why validate the delta?** To prove the run tested the declared threat model rather than an accidental multi-field mutation.
4. **What changes in the review attack?** Exactly the designated `recommendation_code` field.
5. **What is ASR?** Successful attacks divided by eligible clean-baseline examples, using the frozen success definition.
6. **Why report the denominator?** Percentages without eligibility counts conceal exclusions and instability.
7. **What is clean utility?** Target performance before attack; it prevents crediting attacks against an already broken system.
8. **What is an attack family?** A group sharing a manipulation mechanism, used for stratified analysis rather than pooled anecdotes.
9. **Why version prompts?** Prompt changes can alter both susceptibility and baseline performance.
10. **Why hash datasets?** The same filename can contain different examples; a hash binds results to exact content.
11. **What does a confidence interval express?** Sampling uncertainty under its stated estimator, not general validity.
12. **Why bootstrap?** It estimates uncertainty without assuming a simple parametric sampling distribution, subject to independence assumptions.
13. **Can fixture ASR be called real-model ASR?** No; fixture/mock evidence must remain labelled.
14. **Can development ASR be called held-out?** No; selection on the same data invalidates that claim.
15. **What is a targeted attack?** Success requires a specified target behavior, not merely any output change.
16. **What is an untargeted attack?** Success is a defined degradation or divergence regardless of a particular target output.
17. **Why preserve failed attacks?** They reveal boundary conditions and prevent survivorship-biased reporting.
18. **What is contamination?** Information from evaluation examples influences design, prompting, or selection in a way inconsistent with the split.
19. **How should duplicates be handled?** Detect and document them before evaluation; never silently count them as independent evidence.
20. **What does the demo attack prove?** The validated software path can induce a message-level decision flip on designed synthetic pairs.
21. **What does it not prove?** Prevalence, real-world exploitability, clinical harm, or cross-model generalization.
22. **Why keep attack text/data outside contracts?** Corpus evolution should not require changing shared interface schemas.
23. **Who supplies the target traces?** Member 1; Member 2 must verify their clean eligibility before scoring attacks.
24. **Who consumes attack artifacts?** Member 4 uses paired clean/attack trajectories; Member 3 may compare internal activations.
25. **What metadata is mandatory?** Run ID/time, commit/diff, dataset hashes, revisions, prompts, seeds, hardware, environment, command, config, raw output.
26. **How do you investigate 100% ASR?** Check for mock targets, trivial labels, leakage, denominator mistakes, duplicated cases, and attack-validator failures.
27. **Why stratify results?** Aggregate rates can hide family-, class-, or case-specific behavior.
28. **What is the ethical boundary?** Use synthetic/authorized data and present defensive research without operationalizing harm against real systems.
29. **What should Member 2 show live?** The clean/attacked message diff and validator proving only the permitted field changed.
30. **What is the next credible evidence step?** Run the frozen corpus against a qualified model/configuration with preregistered metrics and untouched evaluation data.

## Handoff checklist

Record corpus version and hashes, eligibility counts, clean utility, per-family outcomes, uncertainty method, exclusions, and raw output. Get M1 confirmation of target correctness and M4 confirmation that paired traces retain stable identifiers.

## O–T. Cross-member knowledge, glossary, commands, failures, limits, future

Understand M1 clean eligibility, M3 clean/attack alignment, and M4 mediation denominators. `ASR` is attack success rate; `threat model` is the allowed adversary; `stratum` is a reported subgroup. Run `python -m pytest tests/unit/ -v` and relevant attack runners from their YAML configs. Debug suspicious rates by checking target correctness, duplicates, deltas, eligibility, leakage, and aggregation. Current corpora are synthetic/development-scale; later external benchmarks require qualification and preregistration.

