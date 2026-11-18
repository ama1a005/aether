# AETHER Complete Study Guide

**Status date:** 18 November 2026
**Audience:** beginners, project members, examiners, maintainers, and future researchers
**Authority order:** `RESEARCH_CONTRACT.md` > executed result artifacts > current source/tests > planning documents
**Current scientific state:** implementation-rich but evidence-incomplete; CORE-02 has completed and CORE-03 remediation freeze is the active gate

---

## 1. How to use this book

This guide teaches AETHER from first principles, then connects those concepts to
the repository and the evidence that actually exists. It deliberately separates
four ideas that are often confused:

1. **Designed:** a feature appears in `Phase1Project.md` or
   `4_ProjectDescription.md`.
2. **Implemented:** executable code exists.
3. **Software-verified:** unit, integration, regression, or synthetic tests pass.
4. **Experimentally supported:** a real execution produced immutable raw output,
   a manifest, hashes, and a result that passed an independent verifier.

A fifth state, **publication-supported**, additionally requires appropriate
held-out evaluation, baselines, statistics, limitations, and an honest claim
boundary. AETHER has not reached that final state.

Do not convert a lower evidence level into a higher one merely because a demo is
convincing or a test passes. That distinction is the most important lesson in
the repository.

---

## 2. AETHER in plain language

Imagine two AI agents cooperating:

- **Agent A, the sender**, reads evidence and produces a recommendation.
- The recommendation is placed in a structured **message**.
- **Agent B, the receiver**, reads that message and makes the final decision.

An attacker changes information used by the pipeline. The final decision becomes
unsafe or incorrect. A black-box security test can tell us that the attack
worked, but not *how the failure travelled through the two agents*.

AETHER tries to answer a deeper question:

> Which computations inside Agent A, which fields in the A-to-B message, and
> which computations inside Agent B are causally necessary for the attacked
> decision—and where should an intervention be placed to repair the system with
> the least damage to clean behavior?

The easy analogy is a relay race. Agent A is runner one, the message is the
baton, Agent B is runner two, and the final decision is the finish. Seeing the
team lose does not tell us whether runner one took the wrong route, the baton was
altered, or runner two misread it. AETHER records and intervenes at each stage.

The difficult technical version is a **heterogeneous causal-mechanism discovery
problem** spanning neural states and a discrete communication boundary.

---

## 3. What the project is—and is not

### 3.1 The research identity

The frozen research contract defines AETHER as a cross-agent causal
circuit-discovery framework. Its intended object spans:

```text
sender internal components
        ↓
structured message components
        ↓
receiver internal components
        ↓
final outcome
```

The platform includes attacks, MCP/FHIR tools, multiple agents, a frontend,
reinforcement learning, causal interventions, benchmarks, reports, and
reproducibility infrastructure. These make the experiment possible; they are not
automatically novel.

### 3.2 What is claimed as novelty

The contract’s hierarchy is:

- **N1 — Cross-agent causal circuit discovery.** Build and test a causal object
  that crosses sender internals, the explicit message, receiver internals, and
  outcome.
- **N2 — Heterogeneous cross-boundary search/formalism.** Search over different
  kinds of objects and intervention operators without pretending they are all
  identical neurons.
- **N3 — Mechanism-guided intervention selection.** Use the discovered mechanism
  to choose where to intervene, rather than always repairing a fixed location.

The newer planning language calls the graph a **Distributed Causal Mechanism
Graph (DCMG)** and the edge-testing discipline the **Bridge Verification
Protocol (BVP)**.

### 3.3 What is explicitly not novel

The contract forbids presenting the following as the contribution:

- MCP tool poisoning;
- RL-based circuit search in general;
- multi-agent systems in general;
- ordinary activation patching;
- dashboards or LLM-generated code;
- the medical/IoMT story;
- use of Qwen, FHIR, RAG, or an MCP server by itself.

These are infrastructure, methods, attack sources, or evaluation settings.

### 3.4 Why the novelty had to be narrowed

Earlier project plans combined many fashionable components. Prior-art review
showed that tool poisoning, cross-agent influence, RL discovery, and
mechanistic interventions already existed separately. A defensible project
therefore cannot say “we combined AI agents, MCP, RL, and interpretability.” It
must test the narrower falsifiable proposition that a distributed internal
mechanism can be localized across an explicit agent boundary with incremental
value over message-only and receiver-only baselines.

---

## 4. Foundations for beginners

### 4.1 Agent

An agent is a program that observes inputs, optionally calls tools, maintains
state, and produces actions or messages. In AETHER, “agent” does not imply
consciousness or autonomy. It is an execution role.

### 4.2 Large language model

A language model maps tokens to probability distributions over future tokens.
Internally, a transformer repeatedly applies attention and MLP computations to
a **residual stream**. AETHER’s real primary model is the immutable
`Qwen/Qwen2.5-1.5B-Instruct` revision
`989aa7980e4cf806f80c7fef2b1adb7bc71aa306`.

### 4.3 Transformer layer, attention head, and MLP

- A **layer** is one repeated transformer block.
- **Attention** moves information between token positions.
- An **attention head** is one sub-computation within attention.
- The **MLP** transforms each token’s representation nonlinearly.
- The **residual stream** is the shared vector representation updated by these
  components.
- `pre_o_proj` means the head representation before attention heads are mixed by
  the output projection. It is useful because an individual head remains
  addressable there.

### 4.4 Activation

An activation is a numerical tensor produced during a model forward pass. It is
not automatically meaningful. A difference between clean and attacked
activations is correlation until an intervention changes the outcome.

### 4.5 Hook

A hook is a callback attached to a model component. A capture hook records a
tensor. An intervention hook replaces or edits it. A capture-only hook must pass
**non-interference**: it must not change logits or outputs beyond the declared
tolerance.

### 4.6 Causation versus correlation

If a neuron becomes active whenever an unsafe decision occurs, it is correlated
with that decision. To claim causal relevance, AETHER changes that component
while holding the rest of the execution protocol fixed and measures the
downstream effect.

### 4.7 Counterfactual and intervention

A counterfactual asks: “What would the attacked run have produced if this one
variable had taken its clean-run value?” Activation patching approximates that
question by inserting a clean activation into an attacked execution.

### 4.8 Mediator

A mediator is an intermediate variable through which one variable affects
another. The A-to-B message is an observable mediator. Sender and receiver
activations are proposed internal mediators.

### 4.9 MCP

MCP is a protocol boundary through which a model or agent can discover and call
tools. In the review system, FHIR-related tools may be exposed through MCP. MCP
connectivity is independent of Qwen inference. A working MCP server does not
prove the model works, and installed CUDA does not prove MCP works.

### 4.10 FHIR

FHIR is a healthcare data interoperability standard. AETHER’s medical-style
demo uses synthetic educational cases and FHIR-shaped evidence. It is not a
clinical system and makes no clinical-validity claim.

---

## 5. End-to-end system architecture

### 5.1 Behavioral data path

```text
CaseRecord
   ↓
deterministic or external MCP/FHIR tools
   ↓
Agent A / sender
   ↓
MediatorMessage
   ↓            attack may alter an authorized field
Agent B / receiver
   ↓
decision and RunTrace
```

The main implementation is under `target/`, `attacks/`, and `contracts/`.

### 5.2 Mechanistic data path

```text
aligned clean and attacked prompts
   ↓
Qwen sender forward passes → captured sender activations
   ↓
generated clean/attacked messages
   ↓
Qwen receiver forward passes → captured receiver activations
   ↓
intervention at selected components
   ↓
changed decision logit margin
```

The implementation is primarily under `instrumentation/`, `causal/`,
`discovery/`, and `paired_trace/`.

### 5.3 Evidence path

Every accepted run should produce:

```text
raw rows → summary → manifest → hash inventory → independent verifier
                                               ↓
                                      atomic evidence ingestion
```

The manifest binds the result to code commit, dirty/clean state, dataset hashes,
model and tokenizer revisions, prompts, seeds, hardware, Python environment,
command line, configuration, and raw-output path.

### 5.4 Presentation path

The FastAPI backend and React frontend live under `demo/`. They explain the
pipeline, attack, causal analysis, and evidence status. They do not create
scientific evidence. Demo code may import core modules; core modules must never
depend on the demo.

---

## 6. Frozen data contracts

`contracts/schemas.py` defines the common language between team modules. The
schema is frozen because changing a field can silently invalidate attacks,
traces, interventions, and stored results.

Important conceptual records include:

- **CaseRecord / PatientCase:** the versioned input case and expected provenance.
- **AttackDelta / AttackSpec:** exactly what the adversary is allowed to change.
- **MediatorMessage / A2AMessageRecord:** the structured sender-to-receiver
  bridge, including recommendation/decision content and provenance.
- **RunTrace:** the full clean or attacked execution record.
- **ActivationTrace:** model component, token location, shape, dtype, source
  trajectory, and artifact metadata.
- **InterventionSpec:** target, operator, donor, recipient, token position, seed,
  and expected accounting.
- **CircuitResult:** selected components, effects, costs, and evidence metadata.

Contracts are interfaces, not result files. A valid JSON object proves schema
conformance, not scientific correctness.

---

## 7. Target harness and agents

### 7.1 Agent A

Agent A consumes case/tool evidence and produces the mediator message. Its
implementation is in `target/agents/agent_a.py`, with message construction in
`target/a2a/message_builder.py`.

### 7.2 Agent B

Agent B consumes the mediator and produces the decision. Parsing is explicit in
`target/decision_parser.py`; silent normal-looking defaults are forbidden.

### 7.3 Agent C

Agent C is a review/policy agent implemented in `target/agents/agent_c.py` and
`target/three_agent_pipeline.py`. The code path and synthetic acceptance tests
exist. A real-Qwen Agent-C execution package exists, but its required external
evidence is currently missing. CORE-02 is complete, so this package is now
eligible for its separately declared prospective execution when scheduled.

### 7.4 Tools

`target/mcp/tools.py` supplies deterministic evidence transformations.
`demo/mcp_server/server.py` exposes a real MCP SDK boundary for the review demo.
The external WSO2/HAPI path is integrated in `demo/backend/`, with explicit
health and failure behavior. “MCPTox smoke” is a local compatibility/preparation
path, not the official MCPTox benchmark.

### 7.5 Current evidence level

The harness, deterministic tool path, real MCP boundary, three-agent path, and
demo are implemented and software-tested. They establish execution behavior,
not clinical utility or benchmark superiority.

---

## 8. Attack system

### 8.1 Threat model

The adversary is bounded by an explicit attack specification. A valid study must
show that only authorized fields changed. Otherwise an observed failure may be
caused by an accidental multi-field mutation.

### 8.2 Attack families

The design discusses:

- tool-description poisoning;
- tool-output poisoning;
- A2A message tampering;
- implicit preference manipulation.

The standardized causal work uses a tightly controlled decision-code direction
flip so that clean and attacked trajectories can be paired.

### 8.3 Attack success rate

For a targeted attack:

```text
ASR = successful targeted attacks / eligible attack attempts
```

Eligibility is determined before looking at attacked output. A common rule is
that the clean example must be correct. Numerator and denominator must always be
reported; invalid/error cases remain visible.

### 8.4 Clean utility

Clean utility asks whether the unperturbed system performs its intended task. A
high attack rate is meaningless if the clean system is already broken.

### 8.5 Implemented attack features

`attacks/` contains corpus validation, templates, orchestration, evaluation,
statistics, a real-Qwen backend, and an MCPTox adapter. Red-team orchestration
and synthetic MCP paths are implemented. Official external MCPTox/TAMAS results
do not exist.

---

## 9. Paired traces and model qualification

### 9.1 Why pairing matters

A clean run and attacked run must refer to the same underlying case, prompt
version, model, tokenizer, and generation policy. Otherwise activation
differences mix the attack effect with unrelated variation.

### 9.2 Outcome quantity

The primary behavioral quantity is a signed decision margin:

```text
T(x) = logit_unsafe(x) - logit_safe(x)
Δ_full = T(attacked) - T(clean)
```

The exact label orientation is fixed by the experiment; the point is that the
metric uses model scores rather than an unstructured verbal judgment.

### 9.3 Qualification gates

Qualification asks whether the exact model/configuration can support the later
study. It is not circuit evidence.

The retained Qwen qualification passed on 24 balanced development cases:

- 12 clean-correct A decisions and 12 clean-correct B decisions;
- 12 eligible A→B and 12 eligible B→A attacks;
- conditional ASR 1.0 in both directions;
- clean-message rescue and attacked-message induction 12/12 in both directions;
- zero validation/test executions.

The model was CPU float32, not quantized or offloaded. See
`results/phase1/model_qualification/qwen15b_kaggle_20261110/`.

This establishes a controlled behavioral substrate. It may also reveal a
limitation: the task can reward decision-code copying rather than general trust
reasoning. That construct-validity concern must remain in the paper.

---

## 10. Instrumentation and activation capture

### 10.1 Instrumentation acceptance

Before broad capture, IA-G1 tested passive hooks, exact tensor persistence,
pre-`o_proj` head shape, active patch execution, cleanup, and locked-split
isolation. It passed. This says the measurement instrument works on the pinned
model; it does not locate a circuit.

### 10.2 Development capture

DCAP-1 captured 80 activation artifacts and 3,360 paired measurements. The
partition was:

- 16 discovery cases;
- 4 untouched development-audit cases;
- 4 earlier instrumentation-acceptance cases excluded from selection.

All declared traces were captured and round-tripped, qualified predictions were
reproduced, hooks were cleaned up, and validation/test counts remained zero.
The large tensor archive remains external; committed metadata and hashes point
to it. See `results/phase1/development_capture/qwen15b_dcap1_20261111/`.

### 10.3 Candidate selection

Activation differences were used only as a correlational prefilter. Twelve
candidates were selected prospectively for intervention. Selection does not
make them causal.

---

## 11. Causal interventions

### 11.1 Main operators

- **Zero ablation:** replace a target with zero.
- **Mean ablation:** replace it with a declared reference mean.
- **Clean-to-attacked patch:** insert a clean donor activation into the attacked
  run and ask whether the clean behavior is rescued.
- **Attacked-to-clean patch:** insert an attacked donor into the clean run and
  ask whether attacked behavior is induced.
- **Message-field patch:** replace one structured message field.
- **Whole-message patch:** replace the complete mediator.
- **Edge cut:** explicitly interrupt a hypothesized connection in replay.
- **SAE feature intervention:** modify a feature produced by a trained sparse
  autoencoder, subject to checkpoint/provenance/reconstruction gates.

### 11.2 Intervention validity

Every real intervention must record model/tokenizer revision, layer/head/node,
token position, donor/recipient condition, seed, prompt, generation parameters,
output, and metric delta. A patch that was manually tried without these records
does not count.

### 11.3 Negative controls

Controls distinguish genuine specificity from generic replacement damage:

- identity clean-to-clean;
- passive hook;
- irrelevant token position;
- opposite-decision donor;
- shuffled same-decision donor;
- region/count-matched random masks.

---

## 12. The QCI sequence and why the negative result matters

### 12.1 QCI-1: case-specific mediation test

QCI-1 executed 1,344 candidate/control interventions plus 32 message positive
controls with zero invalid/error rows. No internal candidate passed all frozen
specificity predicates. Some receiver patches had large effects, but did not
separate from the shuffled-source control.

The correct conclusion was:

```text
STOP_INTERNAL_CAUSAL_CLAIM
```

This is not an implementation failure. It is a scientifically meaningful
negative result. Thresholds were not weakened after observing it.

### 12.2 Why QCI-1’s control was insufficient for semantic mediation

The shuffled donors stayed within attack direction and therefore preserved the
same clean/attacked decision semantics. The control tested case identity, but
could not distinguish a shared decision-semantic representation from a generic
replacement effect.

### 12.3 QCI-2: prospectively distinct semantic study

Before executing new model work, QCI-2 froze same-decision generalization and
opposite-decision specificity controls while reusing the unchanged 12
candidates. It did not retroactively alter QCI-1.

QCI-2 discovery executed 1,920 candidate interventions and 32 message controls,
1,952 total executions and 5,920 forward steps, with zero invalid/error rows.
Four candidates passed:

- sender layer-22 attention output;
- receiver layer-22 attention output;
- receiver layer-20 head 5 at pre-`o_proj`;
- receiver layer-22 head 7 at pre-`o_proj`.

### 12.4 QCI-2 development audit

All four candidates replicated on four untouched development-audit cases: 160
candidate executions plus 8 message controls, zero invalid/errors, and no
validation/test access.

The permitted statement is **development-only decision-semantic mediation**.
It is not yet a full connected distributed circuit, held-out validation, repair
utility, benchmark superiority, or publication-ready generalization.

---

## 13. DCMG and Bridge Verification Protocol

### 13.1 Graph definition

A DCMG is a typed candidate graph:

```text
G = (V_S ∪ V_M ∪ V_R ∪ V_O, E)
```

where `V_S` are sender nodes, `V_M` message nodes, `V_R` receiver nodes, and
`V_O` outcome nodes. Nodes and edges are hypotheses until intervention evidence
supports them.

### 13.2 Why graph topology is not evidence

Drawing `sender → message → receiver` reflects execution order. It does not show
that a particular layer or head causally carries the effect. Attention weights,
probe accuracy, and temporal precedence are candidate-generation evidence only.

### 13.3 BVP edge tests

- **Sender → message:** intervene in the sender, regenerate the message, and
  measure the declared downstream message quantity.
- **Message → receiver:** modify the message, rerun the receiver, and measure the
  receiver/outcome effect.
- **Receiver → outcome:** preserve incoming message bytes, intervene in the
  receiver, and measure the decision margin.

A connected pathway can be claimed only if its necessary edges individually
pass their frozen tests and controls.

### 13.4 Overlap constraints

Some candidates are nested: `message.whole` overlaps
`message.decision_code`; a complete layer-22 attention output overlaps a head
inside that attention module. The frozen CORE-02 legal-mask system prevents
ambiguous double intervention. It contains 36 legal masks, never constructs an
overlap-invalid mask, and applies each selected internal address exactly once.

---

## 14. Search algorithms

The purpose of search is to find a compact, faithful, low-damage mechanism under
a strict model-call budget.

### 14.1 Matched random

Randomly samples legal masks with region counts matched to the greedy reference.
It answers whether a sophisticated method beats an equally sized arbitrary set.

### 14.2 Greedy

Begins from all four maximal legal masks, removes one retained node at a time,
and selects the best ranked child. It is cheap and interpretable but can miss
synergistic interactions.

### 14.3 Beam search

Keeps the two best current candidates, expanding all legal one-node removals.
It explores more alternatives than greedy at higher cost.

### 14.4 Receiver-only baseline

Searches only the three receiver candidates. It tests whether the distributed
sender/message structure adds value beyond conventional receiver localization.

### 14.5 Flat PPO

Uses reinforcement learning over an overlap-safe node-removal environment. It
is a baseline/method—not the primary novelty.

### 14.6 Heterogeneous graph-aware PPO

The repository also implements an additive hierarchical environment whose
action factorizes:

```text
operation × region × target × intervention operator
```

The observation includes DCMG adjacency, node/edge types, current causal
measurements, remaining budget, cache state, and a bounded query ledger. It can
intervene on nodes, cut edges, or stop. Multi-seed branching-graph acceptance is
synthetic software evidence only; it has not produced real-Qwen publication
evidence.

---

## 15. The RL problem formulation

### 15.1 Markov decision process

An MDP is usually written `(S, A, P, R, γ)`:

- `S`: state;
- `A`: actions;
- `P`: transition rule;
- `R`: reward;
- `γ`: discount factor.

For AETHER:

- **State:** current retained graph/mask, measured effects, benign damage,
  adjacency/type features, cached queries, and remaining budget.
- **Action:** remove/retain/intervene/cut/stop at a legal typed target.
- **Transition:** update the graph and, for a previously unseen mask, execute the
  causal evaluator.
- **Reward:** combine effect preservation, benign preservation, compactness,
  query cost, and a feasible-stop bonus.
- **Terminal condition:** explicit stop, no legal action, or exhausted budget.

### 15.2 Why complete state matters

If the agent cannot observe remaining budget or which masks are cached, the same
visible graph can require different actions. That violates the practical Markov
assumption and contributed to weak earlier PPO behavior. The improved state
contains budget/cache/query-ledger information.

### 15.3 PPO in simple terms

PPO trains a policy to choose actions while limiting how drastically each
update changes the policy. An actor proposes actions; a critic estimates future
return. The clipped objective improves stability. AETHER freezes hidden size,
learning rate, rollout length, update epochs, entropy/value coefficients,
gradient norm, checkpoint selection, and deterministic reload behavior.

### 15.4 Novelty boundary

The project-specific typed MDP is a useful methodological contribution under
N2, but “we used PPO” is not novel. It earns scientific value only if matched
real-model evaluation shows a better quality–cost trade-off than deterministic
baselines.

---

## 16. CORE-02: the active experiment

CORE-02 compares five methods across seeds 11, 22, and 33: 15 method/seed runs.
Every complete mask evaluates 16 cases in two conditions and costs 160 model
forward steps. Per method/seed limits are:

- maximum 32 unique search masks;
- maximum 45 total mask evaluations;
- maximum 7,360 model forward steps.

Caches are independent per method and seed. Identical maximum budgets do not
mean identical consumed budgets; actual consumption must be reported.

The original single notebook proved too fragile and slow. An approved
scheduling-only v2.4 amendment allows disjoint seed shards while leaving every
scientific parameter unchanged. The three notebooks are:

- `notebooks/aether_qwen_core02_seed11.ipynb`;
- `notebooks/aether_qwen_core02_seed22.ipynb`;
- `notebooks/aether_qwen_core02_seed33.ipynb`.

Each runs all five methods for one seed. Checkpoints are uploaded after every
completed mask to a private Hugging Face dataset. A mask is reported complete
only after remote upload succeeds. Shards must pass
`scripts/verify_qci2_matched_search_shard.py`, then the merger rejects missing,
duplicate, overlapping, or mixed-provenance results. The merged bundle must
still pass the original full verifier.

On 18 November 2026, all three shards independently verified, merged, passed the
full verifier, and were atomically ingested. The bundle contains 15 method/seed
runs and 220 real evaluations with zero audit, validation, or test access.

Greedy, matched random, beam, and flat PPO all selected the one-node
`message.decision_code` mechanism for every seed, with faithfulness
`0.9999991177106842` and benign logit-margin damage about `1.43e-5`.
Receiver-only selected `receiver.head.L20.H5.pre_o_proj`, with faithfulness
`0.9085500110247975` and the same benign damage. Thus the message bottleneck is
sufficient under this task; PPO did not improve the terminal mechanism and cost
more. This does not establish a connected multi-region DCMG.

The pinned runner had a metadata-only defect: terminal stop reasons were
recorded, but its budget-ledger state was serialized as `RUNNING` before the
ledger’s `complete()` transition. The strengthened verifier permits this only
for the exact affected source commit and only when all 15 runs have valid
terminal stop reasons, feasible masks, intact raw evidence, and legal budgets.
Future runs serialize `COMPLETE`. No experimental value was rewritten.

---

## 17. Metrics and statistics

### 17.1 Circuit faithfulness

The frozen formula is:

```text
F(C) = 1 - |Δ_full - Δ_C| / (|Δ_full| + ε)
```

`Δ_full` is the full reference attack/intervention effect and `Δ_C` is the
effect reproduced by selected circuit `C`. Faithfulness is not classification
accuracy. A value near one means the selected set reproduces the defined effect.

### 17.2 Operational minimality

A mechanism is locally minimal if removing any selected node causes
faithfulness to fall below the threshold. AETHER does not claim global
minimality unless exhaustive proof exists.

### 17.3 Benign damage

CORE-02 measures absolute change in the clean decision-logit margin, aggregated
as frozen by the proposal. This is a score-space preservation metric. It is not
the same as benign decision accuracy, task utility, clinical safety, or user
preference. The threshold `0.1` is in raw logit-margin units.

### 17.4 Confidence intervals

A confidence interval estimates sampling uncertainty under a declared method.
It does not prove external validity. The evaluation package includes paired
bootstrap confidence intervals, invalid/error denominators, and seed stability.

### 17.5 McNemar test

McNemar’s test compares two paired binary methods using discordant outcomes:
cases A gets right/B wrong versus A wrong/B right. Pairing is crucial because
both methods see the same cases.

### 17.6 Negative controls and ablations

Required comparisons remove sender nodes, message nodes, receiver nodes,
causal intervention, or particular operators; compare whole-message-only,
random, greedy, beam, RL, receiver-only, candidate granularities, attack
families, and eventually model families. An ablation explains what part of the
method creates value.

---

## 18. Calibration evidence

### 18.1 Tracr

Tracr compiles a known reverse program into a transformer-like model. AETHER
tested all eight compiled attention/MLP half-layers over three exact reverse
cases. Baseline, passive-copy, and restored outputs were exact; 15 of 24
target/case ablations changed a non-BOS output. This validates intervention
machinery on known structure, not the Qwen causal claim.

### 18.2 GPT-2 IOI

The pinned GPT-2 IOI calibration used 24 cases with baseline accuracy 1.0 and
zero passive-hook logit difference. The known three-head group achieved
normalized recovery about 0.388 versus matched-random mean about 0.0026, passing
the prospectively declared comparison. Again, this calibrates machinery; it
does not prove the AETHER distributed mechanism.

---

## 19. Sparse autoencoders

A sparse autoencoder (SAE) maps a dense activation into a sparse feature vector
and reconstructs the activation. A feature intervention can be easier to
interpret than editing raw dimensions. The repository implements checkpoint
loading, hashes, model/component provenance, normalization metadata,
reconstruction-error thresholds, and failure handling.

What is missing is a scientifically suitable, pinned, trained SAE checkpoint
for the exact Qwen component. Toy SAE tests prove the interface, not a Qwen
feature claim.

---

## 20. Remediation

### 20.1 Tri-location candidates

Possible repair locations are sender, message, or receiver. The repository
contains deterministic selectors and Pareto-frontier logic under
`remediation/`.

### 20.2 Pareto frontier

A candidate is dominated if another is at least as good on every objective and
better on one. A Pareto frontier keeps non-dominated trade-offs across attack
reduction, clean utility/damage, complexity, and cost.

### 20.3 Current limitation

CORE-02 has now identified and verified the relevant development result. The
remediation comparison must next be prospectively frozen before execution;
locked validation and once-only test remain downstream and unopened.

---

## 21. Benchmarks and datasets

### 21.1 BFCL

BFCL measures function/tool calling. A pinned official package path and disclosed
Qwen adapter are implemented. An official result is missing. Any future score
must be labelled “official evaluator with disclosed AETHER model adapter,” not
an unmodified leaderboard configuration.

### 21.2 AgentDojo

The native execution package, verifier, and ingester are prepared. Official
execution evidence is absent.

### 21.3 MCPTox

MCPTox is an external tool-poisoning benchmark and prior art. A local smoke
result exists, but official execution is blocked by an unresolved reproducible
official evaluator/licensing boundary. Smoke is not official benchmark evidence.

### 21.4 TAMAS

The integration plan and adapter preparation exist. Official-compatible
execution requires its native framework and credentials; evidence is absent.

### 21.5 PTB-XL

PTB-XL provides standardized source provenance for medical-style cases. A
frozen adapter can transform source tasks into the AETHER protocol. The AETHER
task remains a derived experimental artifact, not a claim that PTB-XL directly
contains multi-agent attacks.

### 21.6 Synthetic planted-causality benchmarks

These give known ground truth and are valuable for testing graph recovery,
precision, recall, and search. They are software/method calibration, not external
real-model generalization.

---

## 22. Demo and frontend

The review application includes a FastAPI backend, React/Vite frontend,
synthetic case workspace, pipeline view, attack lab, causal-analysis display,
red-team view, live status, and Phase-1 evidence page.

There are three distinct execution modes:

- **Deterministic/replay:** stable presentation using genuine AETHER interfaces
  but no live Qwen claim.
- **External MCP/FHIR:** real MCP transport to prepared FHIR services.
- **Qualified model path:** only when exact model/cache/runtime gates pass.

The demo must label these honestly. It is incorrect to describe deterministic
MCP tools as evidence that a Qwen model reasoned over them. Likewise, an MCP
SDK server can be real even when the tool implementation is deterministic.

---

## 23. Reproducibility and fail-closed engineering

### 23.1 Fail closed

When evidence prerequisites are missing or inconsistent, execution stops. It
must not silently substitute a toy model, default result, synthetic tensor, or
cached number.

### 23.2 Immutable inputs

Models are pinned by revision; source by Git commit; datasets/configs by hashes;
result bundles by inventories. Hash mismatch means the artifact is different,
even if its filename is unchanged.

### 23.3 Independent verification

The code that produces a bundle is not trusted merely because it exits zero.
Separate verifiers inspect required files, hashes, splits, run counts, budgets,
evidence types, and provenance.

### 23.4 Atomic ingestion

Ingesters verify first, copy through staging, and refuse overwrite. Evidence is
not manually copied into official result directories.

### 23.5 Split discipline

Development discovery can inform design. A separate development audit tests
replication without becoming locked validation. Validation is used for frozen
selection. The once-only test is opened only after all upstream choices are
fixed and explicitly authorized.

---

## 24. Development timeline and major observations

1. **Stage 0:** Python 3.11 environment, dependency metadata, tests, smokes,
   manifests, CI, and basic defects were repaired.
2. **Platform construction:** target harness, attacks, MCP boundary, causal
   graph, interventions, search, statistics, demo, and reproducibility tooling
   were implemented.
3. **Real-model qualification:** local RAM blocked Qwen1.5B, so commit-pinned
   Kaggle CPU execution was used. The model qualified behaviorally.
4. **Instrumentation acceptance:** passive and active hook semantics passed.
5. **Development capture:** aligned sender/receiver artifacts were captured.
6. **QCI-1:** case-specific internal mediation was negative. The result was
   retained instead of threshold shopping.
7. **QCI-2:** a separately frozen semantic-control question found four
   development-supported candidates, all replicated on the development audit.
8. **Method freeze:** exact mask semantics, overlap rules, budgets, benign units,
   BVP evidence, and five comparators were reviewed through v2.3.
9. **CORE-02 reliability:** long single-session execution caused repeated loss;
   v2.4 approved seed sharding. Per-mask private remote checkpoints were added
   as execution reliability infrastructure without changing science.
10. **Current point:** three external seed shards must complete, verify, merge,
    and ingest before remediation or locked evaluation.

---

## 25. Current implementation status

### 25.1 Implemented and working as software

- frozen Pydantic/data contracts;
- deterministic target harness and synthetic cases;
- sender, receiver, and Agent-C paths;
- attack corpus, validation, evaluation, statistics, and red-team orchestration;
- MCP SDK boundary and external FHIR/MCP integration;
- Qwen adapter, hooks, pre-`o_proj` heads, capture, patching, cleanup;
- residual, module, head, message, SAE, edge-cut, and path-replay operators;
- cross-agent graph representation and validation;
- random, greedy, beam, receiver-only, flat PPO, and hierarchical graph PPO;
- measured evaluator, budgets, caches, and checkpoint/resume;
- paired statistics, confidence intervals, McNemar, plots, and report code;
- Tracr and GPT-2 calibration paths;
- BFCL/AgentDojo/native external package wrappers;
- real-Qwen red-team, Agent-C, SAE, and second-model packages;
- strict external bundle verification and atomic ingestion;
- Phase-1 completion registry, frontend evidence status, and demo packaging;
- three durable CORE-02 seed notebooks with private remote checkpoints.

### 25.2 Executed real evidence that currently passes

- Qwen2.5-1.5B model qualification;
- Qwen instrumentation acceptance;
- Qwen development activation capture;
- QCI-2 semantic discovery;
- QCI-2 untouched development audit;
- Tracr intervention calibration;
- GPT-2 IOI causal calibration;
- method-freeze approvals and split protections.

### 25.3 Important executed negative evidence

- QCI-1 found no case-specific internal candidate that passed every specificity
  control. It remains a valid negative result.
- Earlier local larger-model attempts were blocked by memory readiness; installed
  CUDA alone was not sufficient.
- Several earlier notebook attempts failed before evidence production because
  of hash portability, missing logs, token replay, session loss, or incomplete
  checkpointing. Failures were not promoted as results.

### 25.4 Software test status

After CORE-02 ingestion and the metadata corrections, the complete
model-independent suite reported **473 passed and 5 skipped** with one harmless
Windows `.pytest_cache` permission warning. The skipped tests require declared
real external environments; they are not hidden failures.

---

## 26. What is not done

The live execution registry reports overall evidence **INCOMPLETE**.

### 26.1 Immediate missing gate

CORE-02 is complete. The immediate missing core gate is a prospectively frozen
and executed mechanism-guided remediation comparison based on that result.

### 26.2 Blocked downstream core work

- mechanism-guided remediation result;
- locked validation result;
- once-only test result.

These cannot be honestly completed before their dependencies.

### 26.3 Missing external/supporting evidence

- official BFCL execution;
- official MCPTox result;
- official-compatible TAMAS result;
- trained-SAE Qwen result with a pinned suitable checkpoint;
- real-Qwen red-team result;
- real-Qwen Agent-C result;
- second-model qualification and comparison.

### 26.4 Missing final integration evidence

- final verified report manifest;
- final tables/figures generated only from all required verified inputs;
- publication-ready claim review;
- complete final hand-in evidence bundle.

### 26.5 Claims that remain forbidden

- a validated complete distributed internal circuit;
- superiority of PPO/DCMG search on real Qwen;
- mechanism-guided repair effectiveness;
- held-out generalization;
- official benchmark superiority;
- clinical safety or correctness;
- generalization to arbitrary multi-agent systems.

---

## 27. Four-person ownership and study responsibilities

Ownership means review responsibility, not exclusive Git authorship. Everyone
must understand the full pipeline.

### 27.1 Member 1 — Target and protocol

Primary paths: `target/`, `configs/experiments/`.
Must explain case loading, tools, sender, mediator, receiver, trace provenance,
clean utility, model/replay distinction, and failure behavior.
Handoff: aligned clean/attacked traces and stable message semantics.

### 27.2 Member 2 — Attacks, benchmarks, and evaluation

Primary paths: `attacks/`, `data/attack_cases/`, `benchmarks/`.
Must explain threat model, exact delta validation, eligibility, ASR denominator,
clean utility, attack-family stratification, uncertainty, official-versus-smoke
benchmark boundary, and leakage prevention.
Handoff: validated deltas, per-case outcomes, metrics, and corpus hashes.

### 27.3 Member 3 — Internal causality and search

Primary paths: `instrumentation/`, `causal/interventions/`, `discovery/`.
Must explain transformer components, hooks, non-interference, capture, patching,
head semantics, token alignment, faithfulness, controls, query budgets, search
methods, PPO, and why activation differences are not causal proof.
Handoff: precise intervention records and component evidence.

### 27.4 Member 4 — Distributed mediation and constrained repair

Primary paths: `causal/`, `paired_trace/`, `remediation/`, Phase-1 runners.
Must explain DCMG, BVP, message rescue, edge evidence, overlap constraints,
minimality, development/audit/validation boundaries, tri-location remediation,
and final claim limits.
Handoff: verified graph/effect artifacts, repair candidates, and evidence labels.

### 27.5 Shared integration responsibility

All members own `demo/`, integration tests, manifests, paper interpretation, and
the obligation to preserve negative results.

---

## 28. How to explain the demo in a viva

1. Select a synthetic case and show its provenance.
2. Show tool evidence and distinguish deterministic tools from MCP transport.
3. Run/show the clean path: sender message and receiver outcome.
4. Show the attacked field-level delta and validator.
5. Show the attacked outcome and ASR eligibility.
6. Patch the clean message into the attacked receiver path and show message
   rescue.
7. Explain that message rescue is causal message-level evidence, not an internal
   neural circuit.
8. Show the candidate graph and label untested edges as hypotheses.
9. Show evidence status: what is executed, missing, blocked, or synthetic.
10. State the next gate: prospectively freeze and execute CORE-03 remediation
    without opening protected validation or test data.

Never say “the model is live” unless the exact qualified model path is active.
Never call a replay a real-model run. Never call smoke output an official
benchmark result.

---

## 29. Commands and artifact map

### 29.1 Python verification

```powershell
python -m pytest tests/unit -v
python -m pytest tests/integration -v
python -m pytest tests/regression -v
python -m experiments.phase1.single_agent_circuit_smoke
python -m experiments.phase1.cross_agent_smoke
python scripts/smoke_test.py
```

### 29.2 Phase status

```powershell
python scripts/audit_phase1_completion.py
python -m scripts.phase1_execution_status
```

### 29.3 CORE-02 shard verification and merge

```powershell
python -m scripts.verify_qci2_matched_search_shard <seed-directory>

python -m scripts.merge_qci2_matched_search_shards `
  --shard <seed11-directory> `
  --shard <seed22-directory> `
  --shard <seed33-directory> `
  --output <new-merged-directory>

python -m scripts.verify_qci2_matched_search_bundle <new-merged-directory>
```

### 29.4 Authoritative artifact locations

- Model qualification: `results/phase1/model_qualification/`
- Instrumentation acceptance: `results/phase1/instrumentation_acceptance/`
- Development capture: `results/phase1/development_capture/`
- QCI/QCI-2: `results/phase1/causal_interventions/`
- Method decisions: `results/phase1/method_freeze/`
- Calibration: `results/calibration/`
- Current execution registry: `configs/phase1_execution_registry.yaml`
- Completion gates: `configs/phase1_completion_gates.yaml`

---

## 30. Common misunderstandings

**“The model changed after a patch, so we found a circuit.”**
No. Generic replacement can change behavior. Specificity controls and accepted
edges are required.

**“Attention shows where the model looked.”**
Attention is a computation, not a complete causal explanation. Intervene.

**“The demo uses real MCP, so the model experiment is real.”**
Transport realism and model evidence are separate.

**“CUDA is installed, so Qwen must work.”**
PyTorch compatibility, CUDA visibility, host RAM, GPU memory, dtype, model
weights, tokenizer, and runtime headroom all matter.

**“A 100% ASR proves a serious vulnerability.”**
Not by itself. Check clean utility, eligibility, task construction, attack
specificity, leakage, and external validity.

**“Synthetic tests are fake and useless.”**
They are valuable software/calibration evidence when labelled correctly. They
are not substitutes for real-model or held-out evidence.

**“A negative hypothesis means the project failed.”**
No. QCI-1 constrained the claim. The mistake would be hiding it or changing the
threshold after observing it.

**“The project is done because all code exists.”**
No. Evidence-bearing execution and locked evaluation remain.

---

## 31. Threats to validity

- The behavioral task may measure decision-code copying more than general trust.
- QCI-2 evidence is development-scale and model-specific.
- Candidate selection can miss distributed or nonlinear mechanisms.
- Patching may introduce out-of-distribution activations.
- Greedy/beam/RL comparisons depend on exact matched accounting.
- CPU float32 is reproducible but expensive and not representative of deployment.
- Three seeds are useful but limited.
- Synthetic medical cases do not establish clinical realism.
- External benchmark execution is incomplete.
- No locked validation/test causal conclusion exists yet.
- One primary model cannot establish cross-model generality.

These limitations should appear in the final paper, not be treated as private
implementation notes.

---

## 32. Exact next steps

1. Freeze the CORE-03 message-versus-receiver remediation protocol before any
   new model execution.
2. Obtain exact-hash human approval for that protocol.
3. Execute, independently verify, and atomically ingest remediation evidence.
4. Freeze and authorize locked validation; open it only once permitted.
5. Freeze the final choice and execute the once-only test.
6. Run required official/supporting benchmark packages where protocol and
    credentials permit.
7. Generate the final report only from verified manifests.

If CORE-02 is negative or budget-incomplete, retain it. The project should pivot
its final claim to the strongest evidence actually supported rather than
fabricating completion.

---

## 33. Compact glossary

- **A2A:** agent-to-agent communication.
- **Ablation:** removal/replacement of a component’s contribution.
- **Activation:** internal tensor produced by a model.
- **ASR:** attack success rate on eligible attempts.
- **BVP:** Bridge Verification Protocol; intervention tests for cross-boundary
  edges.
- **Candidate:** a hypothesis selected for testing, not accepted evidence.
- **Causal patch:** controlled replacement of a variable from a donor run.
- **Circuit:** selected component set proposed to mediate a behavior.
- **Clean utility:** unperturbed task performance.
- **DCMG:** typed graph spanning sender, message, receiver, and outcome.
- **Development audit:** untouched development subset used for replication,
  distinct from locked validation.
- **Faithfulness:** reproduction of a defined causal effect.
- **FHIR:** healthcare interoperability standard used in the demo context.
- **Hook:** callback observing or modifying a model component.
- **Manifest:** reproducibility metadata binding a result to exact inputs/code.
- **Mask:** legal selected set of candidate nodes/interventions.
- **MCP:** protocol for discovering and calling tools.
- **Mediator:** intermediate variable carrying an effect.
- **Minimality:** inability to remove a selected node without violating the
  threshold; local unless globally proven.
- **PPO:** Proximal Policy Optimization.
- **Pre-`o_proj`:** per-head representation before attention output projection.
- **Provenance:** origin and transformation history of data/artifacts.
- **QCI:** Qwen causal-intervention study.
- **SAE:** sparse autoencoder.
- **Shard:** one seed’s complete five-method CORE-02 execution.
- **Smoke test:** bounded integration check, not scientific validation.
- **Specificity control:** comparison showing an effect is tied to the intended
  variable rather than generic replacement.

---

## 34. Final one-minute answer

AETHER is a mechanistic security framework for a two-agent tool-using pipeline.
It pairs clean and attacked executions, captures internal sender and receiver
states, treats the structured A-to-B message as an explicit mediator, and uses
controlled interventions to test a typed distributed causal graph. Its novelty
is the cross-boundary causal discovery and bridge-verification discipline, not
MCP, RL, or tool poisoning. The real Qwen model has passed qualification,
instrumentation, capture, semantic discovery, and a development audit. A prior
case-specific mediation hypothesis was correctly negative. Four
decision-semantic candidates replicated, and the matched five-method,
three-seed CORE-02 search completed. Its stable result was a sufficient single
message decision-code node; receiver-only was feasible but less faithful, and
PPO gave no terminal improvement. Therefore the codebase is substantially
implemented and tested, while remediation, locked evaluation,
official benchmarks, second-model evidence, and the final publication report
remain incomplete.
