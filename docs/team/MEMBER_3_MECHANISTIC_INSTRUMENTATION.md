# Member 3 — Mechanistic Instrumentation Guide

## A. Full project context

AETHER moves from behavioral attack measurement to causal localization across two agents. Mechanistic instrumentation observes and perturbs internal model state; it becomes research evidence only when aligned to the frozen protocol and outcome metric.

## B. Member responsibility

Member 3 owns activation capture, non-interference, component interventions, and circuit evidence. Study `mechanistic/`, `interventions/`, and `experiments/phase1/single_agent_circuit_smoke.py`. The central obligation is causal precision: observing an activation is not the same as showing that it changes behavior.

Inputs are qualified models and paired traces; outputs are activation traces, intervention records, component rankings, faithfulness curves, and random-baseline comparisons with full manifests.

## C–G. Code, flow, algorithms, models, and config

Follow model adapter loading, hook registration, tensor capture, intervention application, scoring, greedy pruning, and random sampling. Addresses must specify model revision, module/layer/head, token position, tensor shape, and dtype. Configuration freezes capture points, patch source/destination, generation step, metric, seed, device/dtype, and memory policy.

## H–J. Tests, experiments, and negative results

Non-interference tests precede causal tests. Shape/alignment tests prevent invalid patches. Synthetic known-path recovery tests algorithms; real-model development runs test feasibility. Null localizations and MQ-HW1's memory-gate failure remain visible and prohibit validation claims.

## K–L. Demo and code review preparation

Explain an activation hook, a patch, and faithfulness using actual source and one manifest. Show evidence cards rather than running an expensive model in the room. Keep the hook registry, intervention implementation, smoke experiment, and blocked qualification artifact ready.

## M–N. Thirty likely questions with answers

1. **What is an activation hook?** A registered callback that observes or modifies a specified model component during a forward pass.
2. **What is non-interference?** With capture enabled but no intervention, outputs/logits match the unhooked reference within the declared tolerance.
3. **Why test it first?** A hook that changes behavior invalidates every downstream causal comparison.
4. **What is an `ActivationTrace`?** A structured record linking captured tensors/components to a run, token positions, and provenance.
5. **Why avoid committing tensors?** They are large, model-dependent artifacts and may expose input information; manifests point to controlled storage.
6. **What is zero ablation?** Replacing a selected activation with zero during execution.
7. **What is mean ablation?** Replacing it with a defined reference mean, whose dataset and computation must be recorded.
8. **What is activation patching?** Replacing an activation in one trajectory with the corresponding activation from another.
9. **What makes patching causal?** The controlled intervention changes the candidate variable while other run conditions are held fixed.
10. **What is a component?** A preregistered address such as layer/head/module and token position, not a post-hoc verbal label.
11. **What is a circuit?** A selected set of components hypothesized to mediate the behavior under the defined intervention and metric.
12. **What is faithfulness?** Recovery of the reference causal effect by the selected set under the frozen formula.
13. **Is faithfulness accuracy?** No; it measures intervention-effect reproduction, not task correctness.
14. **Why compare random circuits?** To determine whether an equally sized arbitrary set often performs similarly.
15. **What is a greedy pruner?** An algorithm selecting/removing components iteratively according to measured causal contribution.
16. **What risk does greedy search create?** Interactions may make locally optimal choices miss distributed or synergistic circuits.
17. **Why fix seeds?** Sampling, ordering, and model generation can otherwise change rankings and baselines.
18. **Why capture clean and attacked runs?** Their aligned difference supplies candidate locations and patch sources.
19. **What alignment is required?** Model revision, tokenizer, prompt template, relevant token mapping, component naming, and case identity.
20. **What if sequence lengths differ?** Use an explicit alignment policy and report unmapped positions; never silently index mismatched tokens.
21. **What does the toy known-path result establish?** The algorithm can recover an injected causal structure under controlled conditions.
22. **What does it not establish?** That the same components exist or generalize in a real language model.
23. **What is development localization?** Circuit discovery on data/configurations used to make design choices; it is not validation.
24. **Why preserve negative localization?** It constrains claims and guides changes without selection bias.
25. **What is the Qwen qualification gate for?** To verify that the intended real model can load, capture, and intervene within resource and fidelity constraints.
26. **Why did MQ-HW1 not advance?** The larger model failed the local host-memory readiness gate, so no success claim is permitted.
27. **Is installed CUDA sufficient?** No; model execution also requires compatible PyTorch/CUDA visibility and enough host/GPU memory headroom.
28. **Who consumes activation traces?** Member 4 builds cross-agent candidates; Member 1 uses results to verify target integration.
29. **What should Member 3 show live?** Evidence-tier cards, hook non-interference rationale, one intervention definition, and the blocked gate honestly.
30. **What is the next step?** Rerun the bounded qualification only with verified resources, then proceed according to its predeclared decision rule.

## Handoff checklist

Provide exact model/tokenizer revisions, hook addresses, tensor shape/dtype, token alignment, intervention source and destination, metric formula, seeds, hardware, and raw artifacts. Confirm non-interference before sharing any localization claim.

## O–T. Cross-member knowledge, glossary, commands, failures, limits, future

Know M1 trace boundaries, M2 attack pairing, and M4 graph-edge use of activations. `Hook` observes/modifies a module; `ablation` removes a signal; `patch` substitutes a source signal; `faithfulness` measures causal-effect recovery. Run the unit suites and `python -m experiments.phase1.single_agent_circuit_smoke`. Diagnose wrong shapes, stale hooks, token misalignment, device/dtype mismatch, OOM, and changed logits in capture-only mode. Current localization is development-scale; future work depends on the qualification gate and held-out confirmation.

