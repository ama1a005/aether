# Member 4 — Cross-Agent Causal Mediation Guide

## A. Full project context

AETHER's current defensible research focus is a causal account of how a bounded attack propagates from sender through an explicit mediator to receiver and outcome. The other three subsystems create trustworthy inputs; this subsystem represents hypotheses and tests them.

## MCP evidence boundary

FHIR retrieval and adaptation occur before Agent A. The mediator remains the Agent A-to-Agent B boundary and message rescue patches it. BVP message evidence does not imply an internal neural mechanism.

## B. Member responsibility

Member 4 owns the cross-agent candidate graph, message-bridge interventions, mediation metrics, and claim boundary. Study `causal/candidate_graph/cross_agent_graph.py`, the mediation modules under `causal/`, and `experiments/phase1/cross_agent_smoke.py`.

Inputs are aligned clean/attack protocol and activation traces; outputs are typed graphs, intervention records, edge/component selections, recovery metrics, and provenance-linked summaries.

## C–G. Code, flow, algorithms, models, and config

Trace node/edge construction in `causal/candidate_graph/cross_agent_graph.py`, bridge patching, outcome scoring, greedy graph pruning, and known-path evaluation. Nodes require stable addresses and roles; edges are hypotheses until intervened upon. Config freezes candidate scope, patch direction, metric formula, eligibility, seeds, and artifact paths.

## H–J. Tests, experiments, and negative results

Unit tests cover graph validity and metric edge cases; synthetic benchmarks test ground-truth recovery; cross-agent smoke checks composition. Development graph selection is not held-out confirmation. Missed known-path edges, null patches, and blocked model qualification constrain claims.

## K–L. Demo and code review preparation

Show clean, attacked, and patched messages beside their outcomes. Open the actual bridge intervention and recovery metric implementation. Clearly distinguish whole-message rescue from neuron/head localization.

## M–N. Thirty likely questions with answers

1. **What is the cross-agent graph?** A candidate causal graph connecting sender components, explicit message fields, receiver components, and outcome.
2. **Why call it a candidate graph?** Its edges encode hypotheses to test, not automatically established causation.
3. **What is a message bridge?** The explicit mediator passed from sender to receiver.
4. **Why is it a privileged intervention point?** It is observable, schema-bound, and can be patched without changing hidden model state directly.
5. **What is message rescue?** Replacing the attacked mediator with its aligned clean counterpart and measuring outcome restoration.
6. **What is the clean outcome?** The outcome from the matched unperturbed trajectory under the same frozen conditions.
7. **What is the attacked outcome?** The outcome after the declared, validated attack delta.
8. **What is the patched outcome?** The outcome after a specified clean variable is inserted into the attacked trajectory.
9. **What is normalized recovery?** The fraction of the clean–attacked gap restored by the patch under the contract formula.
10. **Why normalize?** It makes effect restoration interpretable relative to the available gap, while requiring careful zero-gap handling.
11. **What if clean equals attacked?** The example has no attack-induced gap for rescue; follow the contract’s eligibility/undefined policy rather than inventing a score.
12. **Does full message rescue prove an internal circuit?** No; it establishes mediation at the message level for that trajectory.
13. **What is an internal cross-agent path?** A linked hypothesis from sender components through message variables to receiver components and outcome.
14. **How are edges tested?** With controlled interventions/patches and predefined effect metrics, not correlation alone.
15. **What is a known-path benchmark?** Synthetic data with an injected ground-truth causal route used to test recovery machinery.
16. **Why measure precision and recall?** Precision penalizes spurious selected edges; recall penalizes missed ground-truth edges.
17. **Why can F1 be below one with perfect precision?** The method may select no false edges but miss some true ones.
18. **What does bridge accuracy mean?** Correct identification or operation of the injected message bridge under the benchmark definition.
19. **Why pair clean and attacked traces?** Causal comparisons require aligned cases and stable intervention sources.
20. **What identifiers must align?** Case, run pair, model/tokenizer revision, prompts, attack ID, and relevant component/token addresses.
21. **What is causal scrubbing?** Testing whether a hypothesized subgraph suffices under systematic replacement while irrelevant variables are controlled.
22. **What is a confounder here?** A variable affecting both candidate mediator and outcome that is not controlled by the paired design/intervention.
23. **Does temporal order prove an edge?** No; it only constrains plausible direction.
24. **Why retain outcome nodes explicitly?** It forces every mechanistic claim to connect to the defined behavior rather than activation differences alone.
25. **What does the review rescue establish?** Actual core patching restores the designed synthetic receiver outcome for the selected pair.
26. **What does it not establish?** Population generalization, clinical validity, or held-out neural-circuit discovery.
27. **Who supplies inputs?** M1 supplies protocol traces, M2 supplies validated deltas, and M3 supplies aligned activation traces.
28. **What must Member 4 return?** Graph specification, tested interventions, effect estimates, uncertainty/eligibility, and provenance-linked artifacts.
29. **What should Member 4 show live?** The attack diff, clean-message patch into the attacked run, restored outcome, and exact claim boundary.
30. **What is next after model qualification?** Run preregistered paired traces, test candidate edges, and reserve untouched cases for confirmation.

## Handoff checklist

Validate pair alignment and attack deltas, state every node/edge address, preserve intervention direction, log the clean/attack/patch outputs, compute metrics only on eligible gaps, and label development versus validation evidence.

## O–T. Cross-member knowledge, glossary, commands, failures, limits, future

Know M1 mediator semantics, M2 threat-model validity, and M3 patch alignment. `Mediator` is an intervenable bridge; `candidate edge` is a hypothesis; `recovery` is restored clean–attack gap; `known path` is injected ground truth. Run unit/regression suites and `python -m experiments.phase1.cross_agent_smoke`. Debug pair IDs, directions, zero denominators, stale component addresses, and outcome-scale mismatches. Current evidence is bounded and largely developmental; future work is preregistered qualified-model pairing and untouched confirmation.
