# AETHER — ProjectDescription.md

> **Implementation note (19 October 2026):** The removable review UI now separates live local-Qwen + official MCP stdio execution, deterministic fallback, and verified replay. The live path is implemented but remains unaccepted until the isolated GPU environment installs and the 12-case qualification runs. This does not change frozen scientific claims or turn demo fixtures into validation evidence.

**Platform/project working title:**  
**AETHER: A Mechanistic Security Analysis and Remediation Platform for MCP/A2A Multi-Agent Systems**  
**Phase 1 paper working title:**  
**AETHER: Intervention-Based Distributed Causal Localization of Adversarial Trust Failures in MCP/A2A Multi-Agent Systems**

**Project type:** Final-Year B.Tech Research Project  
**Team size:** 4 students  
**Project window covered by this document:** 4 October 2026 – April 2027  
**Phase 1 deadline:** 16 November 2026  
**Phase 2 deadline:** April 2027  
**Primary research domains:** Mechanistic Interpretability, Multi-Agent Systems, AI Security, Model Context Protocol (MCP), Agent2Agent (A2A), Reinforcement Learning, Causal Intervention, Adversarial Evaluation  
**Demonstration domain:** A small, controlled medical/IoMT-style multi-agent decision pipeline. The medical setting is a high-stakes evaluation harness, not the main novelty claim.

---

## 0. Purpose of this document

This document is the master specification for the AETHER final-year project. It is intentionally much more detailed than a normal proposal or README. Its purpose is to ensure that four students, each using coding agents and AI chatbots, can work in parallel without drifting into four different projects, and can still merge their work into one coherent research system and one coherent paper.

The document defines:

- the research problem and exact project identity;
- what is and is not claimed as novel;
- the major contribution and dependency-ordered extensions;
- the literature position and closest prior art;
- the threat model and experimental assumptions;
- the complete software architecture;
- module-level interfaces and data contracts;
- implementation details for Phase 1 and Phase 2;
- the work split across four team members;
- a merge and integration strategy;
- acceptance tests for every important module;
- the experimental methodology;
- baselines, ablations, metrics, and statistical analysis;
- the Phase 1 paper milestone by 16 November 2026;
- the Phase 2 Q1-journal/patent-quality expansion through April 2027;
- instructions for using coding agents and chatbots efficiently without wasting limited tokens;
- project management rules, code-review rules, and reproducibility requirements;
- risk mitigation and fallback paths;
- patent-relevant mechanisms that may be investigated, without claiming legal patentability;
- a "what not to build" list to protect the project from feature inflation.

This is a living research document. Sections that state novelty must be rechecked against new literature before every external paper or patent submission. A novelty statement is not considered "frozen" merely because it appears in this file.

**October 11, 2026 novelty-hardening and platform-preservation revision:** a reviewer-style prior-art audit identified direct overlap with PropGuard, CASPIAN, CAR, DoVer, NARCBench, MindGuard, MCPFixGen, AttriGuard, AgentSentry, SafeSeek and inter-agent activation-patching work. This revision removes broad "cross-agent circuit" and generic "mechanism-guided remediation" claims, introduces the Distributed Causal Mechanism Graph (DCMG) terminology, makes incremental value over receiver-only/trace-level methods the primary novelty test, and promotes TAMAS/ACIArena as standardized multi-agent evaluation anchors. It also clarifies that the broader pre-existing AETHER platform is preserved: DCMG/BVP is an additive research layer, while red teaming, MCP/A2A integration, receiver-only analysis, search and remediation remain system capabilities, baselines or Phase 2 extensions rather than deleted functionality.

---

## 0.1 Important interpretation of the November 16 deadline

The internal project plan refers to 16 November 2026 as the end of Phase 1 and the "paper publication" milestone. External publication acceptance is not controlled by the team and normally depends on venue review cycles. Therefore, the operational definition used in this document is:

> **By 16 November 2026, Phase 1 must produce a complete, defensible, submission-ready research paper, a reproducible codebase, quantitative results, ablations, figures, tables, limitations, and a working end-to-end demonstration. If an appropriate venue is open, the manuscript should be submitted by or immediately after that milestone.**

The Phase 1 review must not be treated as merely a software demo. The research claim, evidence, and writing must all exist by that date.

---

## 0.2 The guide feedback that caused the project pivot

The project was originally framed too broadly around combinations such as:

- RL-based attack planning;
- multi-agent red teaming;
- MCP/A2A attacks;
- IoMT/medical-device security;
- circuit discovery;
- activation steering;
- automated defense.

The guide correctly identified that broad novelty statements such as "RL-based circuit discovery is new" or "RL + IoMT security is new" are not defensible. Two pieces of prior work are especially important:

1. **MCPTox: A Benchmark for Tool Poisoning Attack on Real-World MCP Servers (AAAI 2026)** already establishes systematic MCP tool-poisoning evaluation at significant scale. Tool poisoning itself is therefore not AETHER's novelty.
2. **MechRL: Reinforcement Learning Agents Perform Circuit Discovery for Mechanistic Interpretability (2026)** already demonstrates reinforcement learning as a method for circuit discovery. RL-based circuit discovery in the abstract is therefore not AETHER's novelty.

The guide's key correction is adopted as the foundation of this document:

> **RL is a method. The scientific contribution must be the causal mechanism being discovered.**

The main research direction is therefore narrowed to:

> **Intervention-based distributed causal analysis of unsafe trust decisions in MCP/A2A agents, explicitly modeling sender internals, the serialized inter-agent message as a mediator, and receiver internals, followed by constrained comparison of repair locations.**

This turns MCP attacks into controlled adversarial stimuli, MechRL into methodological prior art/baseline, and the medical pipeline into an evaluation harness. The research contribution is not a claim that one neural circuit spans multiple models. It is a controlled causal-mediation methodology that asks whether interventions on sender internals, an explicit serialized-message mediator, and receiver internals add measurable explanatory or repair value beyond receiver-only mechanistic analysis, activation/probe baselines, and trace/message-level causal attribution.

---



## 0.3 Additive architecture rule: preserve the AETHER platform, add the new research layer

The October novelty-hardening revision **does not require deleting the earlier AETHER platform**. The correct interpretation is additive:

> **The existing AETHER attack, protocol, observability, mechanistic-analysis, search, and remediation capabilities remain the platform foundation. DCMG/BVP is the new research layer added on top of that platform and is the main Phase 1 scientific contribution.**

This distinction is binding for implementation and writing.

### Platform capabilities that should be preserved when they already exist or can be completed without blocking the paper core

- MCP-enabled tool interaction;
- A2A or equivalent explicit inter-agent message exchange;
- the controlled medical/IoMT-style demonstration workflow;
- deterministic adversarial/tool-poisoning cases;
- Recon/Planner/Exploit/Debrief-style red-team orchestration where already implemented;
- attack corpora and attack-runner infrastructure;
- execution, tool-call, message and provenance logging;
- activation capture;
- activation patching/ablation/intervention machinery;
- receiver-only circuit/mechanism discovery;
- random, greedy, beam and mandatory MechRL-style/RL search infrastructure;
- activation steering and other receiver-side repair primitives;
- message sanitization/patching;
- rollback/replay/recovery primitives;
- remediation scoring and intervention-selection infrastructure;
- dashboards or demonstration UI that already work and do not consume research-critical time.

These capabilities are **system features**, not automatically novelty claims. A feature may remain valuable even when prior art exists. The paper must distinguish:

1. **platform capability** — something AETHER can do;
2. **experimental infrastructure** — something required to run controlled studies;
3. **baseline/prior-art method** — something used for fair comparison;
4. **proposed research method** — DCMG/BVP and the specific comparative causal-localization test;
5. **Phase 2 extension** — an expansion that strengthens generalization, robustness, or technical differentiation.

Functional existing code must not be deleted merely because it is no longer a headline novelty. It should be retained, tested, and reclassified. If an older feature conflicts with the revised causal methodology, preserve it behind a clear interface or historical module and prevent it from contaminating final Phase 1 evidence.

The practical build order is therefore:

```text
existing AETHER platform
        ↓
stabilize + make reproducible
        ↓
standardized benchmark adapters
        ↓
trusted activation/intervention engine
        ↓
receiver-only / trace-level baselines
        ↓
NEW DCMG + Bridge Verification Protocol add-on
        ↓
comparative causal-localization experiment
        ↓
tri-location remediation comparison
        ↓
Phase 2 broadening of the platform
```

## 0.4 Timeline and resource constraints remain binding

The architecture correction does **not** change the major project deadlines or resource assumptions.

- **Intermediate review:** 8 October 2026 — historical checkpoint; its purpose is to show credible progress, not a finished paper.
- **Phase 1 close:** 16 November 2026 — fixed submission-ready paper/reproducible-result milestone.
- **Phase 2:** 17 November 2026 through April 2027 — journal/patent-quality expansion.
- **Team:** four students.
- **AI assistance:** approximately 2–3 coding/research agents or chatbots per student, with finite context/token budgets.
- **Compute:** student-accessible hardware/cloud resources; experiments must be query- and activation-efficient rather than assuming unlimited GPU time.
- **Model access:** prefer small/open-weight models with white-box activation access for the causal core.
- **Data:** public, licensed, synthetic, or benchmark-provided data only; no unverifiable private clinical evidence.
- **Research standard:** all final paper numbers must be reproducible from frozen code/config/data manifests.

### Catch-up rule for dated milestones

A calendar date that has already passed is treated as a **checkpoint, not permission to fabricate completion**. Any unfinished task must be marked honestly in `PROJECT_STATE.md` and rolled into the next active dependency block. Declared Phase 1 features remain mandatory and are dependency-ordered; blocked work is reported rather than silently dropped, and causal validation, standardized baselines, and paper reproducibility remain gates.

The fixed late-Phase-1 protection gates remain especially important:

- early November: method/feature freeze;
- approximately 9–10 November: final full reruns;
- approximately 11–13 November: paper/results assembly and hostile internal review;
- 14–15 November: freeze and presentation preparation;
- 16 November: Phase 1 close.

The team must continue incremental integration before the final week; the project must not wait until 2–3 days before 16 November for the first full merge.

---

# 1. Executive Summary

AETHER is a research framework for discovering **why an adversarial manipulation succeeds inside a multi-agent AI system**, not merely whether it succeeds.

The target class is an MCP/A2A-orchestrated multi-agent system in which one agent can receive data from tools through MCP and pass conclusions, summaries, or decisions to another agent over A2A. In such a system, an attacker may poison a tool description, alter a tool result, manipulate persistent memory, or tamper with an agent-facing message. Standard security evaluation can report attack success rate, malformed messages, or abnormal behavior. It usually cannot answer the deeper causal question:

> Which internal computation caused the receiving system to trust the adversarial information, and how did that causal influence propagate across the boundary between agents?

AETHER treats an unsafe trust decision as a behavior that can be studied through causal intervention. The project captures model activations in the sender and receiver, treats the A2A message as a discrete bridge between two internal computation graphs, constructs a **Distributed Causal Mechanism Graph (DCMG)**, and searches for a compact intervention-validated mechanism under an explicit candidate graph and search budget. Reinforcement learning may be used to search this graph, inspired by MechRL, but RL itself is not the novelty claim.

The intended Phase 1 contribution is a tractable, experimentally validated prototype of this idea. Phase 1 will focus on a deliberately small two-agent or three-agent system and a small open-weight model where white-box activation access is possible. A MCPTox-inspired attack corpus supplies realistic tool-poisoning stimuli. Phase 1 must first establish:

1. a reliable benign/attacked target system;
2. repeatable attack success labels;
3. activation capture and causal intervention primitives;
4. a single-agent circuit-discovery baseline;
5. a distributed sender-message-receiver causal representation;
6. at least one distributed causal-mechanism discovery method;
7. rigorous causal-effect, compactness, stability and negative-control evaluation;
8. one DCMG-informed intervention experiment.

Phase 2 expands the strongest result rather than adding arbitrary features. Possible Phase 2 additions include standardized multi-agent external validation, broader attack families, held-out cross-protocol mechanism stability, memory-poisoning mediation analysis, a second model family, hierarchical/query-efficient mechanism search, constrained intervention-selection refinement, persistence analysis, quantization/edge deployment studies, and larger-scale replication. These are extensions to the core question, not automatically separate novelty claims. Only extensions that directly strengthen the central research question should be promoted to core scope.

The final identity of the project is:

> **AETHER tests whether intervention-based analysis across sender internals, an explicit serialized message mediator, and receiver internals provides additional causal localization and lower-collateral repair options beyond receiver-only and trace/message-level methods.**

---

# 2. The central research problem after the October 2026 novelty stress test

## 2.1 Terminology correction: this is not one neural circuit across two models

A sender model and a receiver model execute separately. The sender's hidden states do **not** flow as tensors into the receiver. What crosses the agent boundary is a serialized artifact such as text, JSON, a structured A2A message, a tool result, or another protocol object. For this reason, the project must not describe the whole sender -> message -> receiver object as one neural circuit.

AETHER uses the following terminology throughout the project:

- **intra-model circuit:** a causally validated set of internal components inside one model execution;
- **message mediator:** the explicit serialized A2A/MCP-derived object transferred between model executions;
- **distributed causal mechanism graph (DCMG):** a heterogeneous causal object containing sender-internal components, message-mediating units, receiver-internal components, and the behavioral outcome;
- **distributed causal pathway:** an intervention-supported path through the DCMG;
- **candidate compact mechanism:** a mechanism returned by the discovery procedure that is compact under the declared candidate graph, intervention operator, data split, and search budget;
- **local minimality:** every single allowed element removal from a returned mechanism violates a predeclared faithfulness/utility constraint. This is the strongest form of "minimal" that Phase 1 may claim unless exhaustive global search is actually feasible.

The terms **minimal causal computation**, **cross-agent neural circuit**, **globally minimal circuit**, and **causally sufficient circuit** must not be used as established facts. They may only appear when describing prior work or a clearly stated hypothesis.

## 2.2 Real problem, stripped of technology labels

Modern agentic systems make decisions through a sequence of separate computations. An upstream model can read untrusted tool metadata or tool output, compress or transform it into a seemingly benign message, and transmit that message to another model. The receiver can then make an unsafe decision even when the final message no longer resembles the original attack payload.

Existing approaches can already answer several important questions:

- MCP benchmarks can measure whether a poisoning attack succeeds;
- multi-agent security benchmarks can measure propagation and system-level compromise;
- trace-level causal methods can identify influential steps, messages, agents, or channels;
- activation probes can detect risky internal states;
- receiver-only mechanistic analysis can localize causal components inside one model;
- remediation systems can sanitize, replay, rollback, or correct contaminated state.

The remaining scientific question is narrower:

> **Does intervention on internal components on both sides of a serialized inter-agent message provide causal localization that is more specific, more explanatory, or more useful for low-collateral remediation than receiver-only mechanistic analysis and trace/message-level causal attribution?**

This is the problem AETHER tests. It is deliberately framed as a comparative, falsifiable question rather than a priority claim.

## 2.3 Primary research question

> **RQ0: In adversarial multi-agent trust failures, can a distributed causal mechanism graph built from sender-internal components, an explicit serialized message mediator, and receiver-internal components recover intervention-validated causal structure that provides measurable value beyond receiver-only mechanistic analysis, activation/probe baselines, and trace/message-level causal attribution?**

The question decomposes into five Phase 1 subquestions:

- **RQ1 — Bridge validity:** Can the project demonstrate a reproducible mediated chain in which sender interventions change the transmitted message, message interventions change receiver computation/outcome, and receiver interventions change the unsafe decision?
- **RQ2 — Incremental causal resolution:** At matched cases and declared budgets, does the distributed method localize a more specific intervention set or yield a better attack-reduction/benign-utility trade-off than receiver-only and trace/message-only baselines?
- **RQ3 — Search value:** Do search procedures over the heterogeneous DCMG provide a useful compact mechanism, and does RL add value over random, greedy, or beam search at matched intervention/query cost?
- **RQ4 — Remediation selection:** Can validation-set causal evidence select a non-dominated intervention among sender-internal, message-level, and receiver-internal candidates without forcing a unique repair location when several work?
- **RQ5 — Held-out generalization:** Does the discovered mechanism retain explanatory or remediation value on attacks, prompts, or scenarios not used during discovery?

Phase 2 asks whether the answer remains stable across model families, attack families, protocols, memory-mediated failures, quantization, longer trajectories, and larger standardized MAS benchmarks.

## 2.4 Falsification is part of the contribution

AETHER is designed so the central hypothesis can fail cleanly. The distributed-mechanism claim is **not supported** if any of the following occurs on the locked evaluation:

1. sender/message/receiver interventions do not form a reproducible mediation chain;
2. receiver-only causal analysis matches the distributed method at similar cost and utility;
3. trace/message-level counterfactual methods match the distributed method's useful localization;
4. the discovered internal components are unstable across seeds or intervention operators;
5. remediation succeeds only by suppressing benign behavior broadly;
6. the proposed search algorithm offers no benefit over a substantially simpler baseline.

A negative answer still produces a legitimate scientific result: it establishes where extra internal access does **not** buy additional causal resolution.

---

# 3. Project identity and paper-safe wording

## 3.1 Recommended working title

> **AETHER: Intervention-Based Distributed Causal Localization of Adversarial Trust Failures in MCP/A2A Multi-Agent Systems**

This title avoids claiming a single neural circuit across separate model executions.

## 3.2 Research-paper identity

> **AETHER evaluates whether causal interventions on sender-model internals, the serialized inter-agent message, and receiver-model internals can localize adversarial trust failures more specifically than receiver-only and trace-level methods, and whether that evidence can select a non-dominated repair under predeclared security, utility, latency, and intervention-footprint constraints.**

## 3.3 Simple viva identity

> We test whether looking inside both AI agents, while treating the message between them as an explicit causal mediator, tells us more about why an attack worked than looking only at the receiving agent or only at the conversation log.

## 3.4 Product-style identity

> AETHER is a white-box audit prototype that turns an attacked multi-agent execution into an intervention-tested distributed causal explanation and a ranked set of repair candidates.

## 3.5 Claims the paper must not make

The Phase 1 paper must not claim any of the following unless a later full-text and citation-chasing audit establishes the precise statement:

- first cross-agent causal analysis;
- first multi-agent interpretability;
- first mechanistic security analysis;
- first MCP/A2A security system;
- first causal repair system for agents;
- first RL subgraph search in multi-agent security;
- first tool-use internal attribution;
- a globally minimal distributed causal mechanism;
- a unique minimal repair point;
- medical/IoMT novelty;
- activation steering novelty;
- generic self-healing novelty.

---

# 4. Reviewer-resistant literature position and corrected claim ledger

This section is intentionally hostile to AETHER's own novelty. A contribution is retained only when the closest known work does not already occupy the same methodological space.

## 4.1 MCP/tool poisoning is established prior art

**MCPTox (AAAI 2026)** establishes standardized evaluation of MCP tool poisoning on real servers/tools. The final AAAI paper reports 45 servers, 353 authentic tools, and 1,348 generated malicious cases; the current public benchmark repository/Inspect implementation marks 36 records as invalid and exposes 1,312 valid attack instances. AETHER must pin the exact release/commit and report the count belonging to that release rather than mixing paper and repository counts.

**MindGuard** performs decision-level inspection for MCP metadata poisoning using an attention-based Decision Dependency Graph and source attribution. Therefore AETHER cannot claim that inspecting internal signals behind poisoned tool decisions is new.

**MCPFixGen** combines internal attention signals, checkpointing, rollback/backtracking, and automated correction for MCP tool poisoning. Therefore AETHER cannot claim that internal-signal-guided MCP remediation is new.

**Implication for AETHER:** MCPTox is an external attack benchmark and MindGuard/MCPFixGen are close internal-attribution/remediation baselines. MCP is the experimental stimulus, not the novelty.

## 4.2 RL search and compact propagation subgraphs are established

**MechRL (2026)** uses reinforcement learning over causal interventions for circuit discovery in GPT-2 Small. RL itself is not novel.

**PropGuard (2026 preprint)** is especially important. Its full text models multi-agent executions as response/full-state spatio-temporal graphs, uses a GE-GRPO-trained inspector to explore compact suspicious propagation subgraphs, verifies harmful propagation, and performs source-guided remediation. Its graph nodes contain responses, received messages, memory, and tool observations rather than per-layer neural activations. This leaves a possible internal-component distinction for AETHER, but eliminates any claim of novelty for "RL + multi-agent propagation graph + compact subgraph + remediation."

**Implication for AETHER:** RL is mandatory comparison machinery but is not the novelty. The scientific comparison is whether internal-component interventions on both sides of a message add value beyond PropGuard/CASPIAN-style trace/state propagation analysis.

## 4.3 Cross-agent causal attribution already exists

**CASPIAN (2026)** performs online cross-channel causal monitoring and attributes source, bridge, and amplifier agents using dynamic influence estimates.

**Causal Agent Replay (CAR, 2026)** models agent trajectories as structural causal models and applies do-interventions plus forward replay to attribute failures to steps, including Monte-Carlo Shapley credit across interacting steps.

**DoVer (ICLR 2026)** actively verifies multi-agent failure hypotheses by targeted intervention and replay. Crucially, DoVer reports that multiple distinct interventions can independently repair one failure. AETHER must therefore not assume a unique repair site.

**AgentSentry (2026)** uses temporal causal diagnostics/counterfactual re-execution around tool-return boundaries and context purification.

**AttriGuard (USENIX Security 2026)** uses action-level causal attribution via counterfactual re-execution to determine whether a tool call is driven by user intent or untrusted observations.

**Implication for AETHER:** "causal attribution," "causal repair," and "intervention-validated debugging" are established categories. The potentially distinct layer is internal-component mediation across two separately executing models plus an explicit message mediator.

## 4.4 Multi-agent interpretability and inter-agent internal effects already exist

**NARCBench / Detecting Multi-Agent Collusion Through Multi-Agent Interpretability (2026)** aggregates activation-probe evidence across agents and reports token-localized collusion signals. This invalidates "first multi-agent activation analysis."

**Not Just RLHF: Why Alignment Alone Won't Fix Multi-Agent Sycophancy (2026)** uses activation patching to causally localize peer-pressure-induced failures in a target model and restores much of the clean-to-pressured correctness gap. This invalidates "first mechanistic analysis of inter-agent influence."

**AgentLens (2026)** performs internal-state safety analysis and representation-level intervention in multi-turn agents.

**Implication for AETHER:** the paper must demonstrate something these do not: an explicit sender-internal -> serialized mediator -> receiver-internal intervention chain, or else narrow the paper to an empirical comparison.

## 4.5 Mechanistic security circuits and safety interventions are established

**SafeSeek (ICML 2026)** extracts sparse safety circuits and uses them for safety-oriented intervention/tuning.

**Mechanistic Interpretability of LLM Jailbreaks via Internal Attribution Graphs (2026)** compares attacked and clean internal graphs and performs node/path/subgraph interventions.

**Circuit Discovery Helps Detect LLM Jailbreaking (2026)** uses edge attribution/subnetwork analysis and ablation for jailbreak behavior.

**Implication for AETHER:** circuit discovery for security is prior art. AETHER extends the evaluation target from a single execution to a distributed, protocol-mediated mechanism only if the experiments support that distinction.

## 4.6 Standard multi-agent security benchmarks now exist

Two 2026 ACL benchmarks materially strengthen the evaluation plan:

- **TAMAS**: 300 adversarial instances, six attack types, 211 tools, five scenarios, plus 100 harmless tasks across multiple MAS configurations.
- **ACIArena**: 1,356 cascading-injection test cases across multiple attack surfaces/objectives and six MAS implementations.

AETHER therefore does not need to argue that standardized multi-agent adversarial evaluation is missing. Instead, these benchmarks become external anchors for attack/utility behavior and Phase 2 generalization.

## 4.7 Corrected claim ledger

| Candidate statement | Status | Paper-safe wording |
|---|---|---|
| "Cross-agent causal analysis is new" | **Do not claim** | CASPIAN, CAR and DoVer already establish causal analysis/intervention across agent traces/channels. |
| "Multi-agent interpretability is new" | **Do not claim** | NARCBench and related activation studies already exist. |
| "RL circuit discovery is new" | **Do not claim** | MechRL is direct prior art; PropGuard also uses RL for propagation-subgraph search. |
| "Mechanistic security analysis is new" | **Do not claim** | SafeSeek, jailbreak-circuit and attribution-graph work already occupy this space. |
| "Tool-poisoning internal attribution is new" | **Do not claim** | MindGuard and MCPFixGen are direct adjacent work. |
| "Mechanism-guided remediation is new" | **Do not claim broadly** | AgentSentry, AttriGuard, MCPFixGen, DoVer and PropGuard already connect causal/diagnostic evidence to repair. |
| "One neural circuit spans both agents" | **Incorrect terminology** | Use a **distributed causal mechanism graph** with separate intra-model components connected by a serialized mediator. |
| "AETHER finds a globally minimal causal mechanism" | **Do not claim** | Say **compact and intervention-validated under the declared candidate graph/search budget**. |
| "AETHER finds the unique repair point" | **Do not claim** | Say **selects a non-dominated candidate from a predefined intervention set**. |
| "Internal interventions on both sides of a message add causal resolution beyond receiver-only and trace-level methods" | **Primary testable distinction** | State as a research question/hypothesis until the locked test supports it. |
| "Tri-location repair selection from distributed internal causal evidence improves the security-utility-cost frontier" | **Secondary testable distinction** | Claim only if held-out comparisons beat fixed-location and trace-level repair baselines. |
| "A released paired activation/message benchmark is useful for distributed causal localization" | **Artifact contribution** | Call it a project benchmark/artifact, never an established standard. |

---

# 5. The narrow defensible research gap

## 5.1 Gap statement

The strongest gap that survives the current literature review is not the existence of multi-agent attacks, causal attribution, internal inspection, circuit discovery, RL search, or remediation. Those all exist.

The unresolved question is whether a **heterogeneous causal object that explicitly combines internal components from two separately executing models with the serialized message between them** can provide additional causal resolution and intervention value beyond methods that operate at only one of these levels.

The project therefore evaluates a method that:

1. starts from paired clean/attacked executions with the attack variable controlled;
2. represents sender internal components, message units, receiver internal components, and the final decision as different node types;
3. establishes sender -> message and message -> receiver bridges by actual interventions rather than attention/correlation alone;
4. searches for a compact intervention-validated distributed mechanism under a fixed candidate graph and budget;
5. compares that mechanism against receiver-only mechanistic analysis, activation/probe methods, and trace/message causal replay;
6. uses validation-only evidence to choose among sender, message, and receiver intervention candidates;
7. reports the complete security-utility-latency-intervention-footprint trade-off on a locked test set.

This is a **comparative methodological contribution**. The project does not need a "first" claim to be publishable if it demonstrates a clear, reproducible improvement in causal resolution or repair efficiency.

## 5.2 Why this gap is technically nontrivial

The heterogeneous boundary creates problems absent from ordinary single-model circuit discovery:

- the two model executions may use different weights or architectures;
- the sender and receiver have separate token positions and activation spaces;
- only the serialized message is transmitted;
- sender interventions must regenerate the mediator before the receiver is rerun;
- message interventions can change tokenization and downstream computation;
- causal links across the boundary cannot be inferred from attention weights alone;
- trace-level methods can appear successful simply by replacing an entire message, so the project must show incremental value in specificity/utility rather than only raw attack removal;
- multiple repair locations may be valid, so optimization is naturally multi-objective rather than single-site attribution.

## 5.3 The experiment that decides whether the gap survives

For the same held-out failures and as comparable a compute/intervention budget as possible, compare:

1. receiver-only activation patching/pruning;
2. activation probe or attention-dependence baseline;
3. trace/message counterfactual attribution/replay;
4. proposed sender-message-receiver DCMG intervention method.

The project survives the novelty stress test only if method 4 produces an advantage that methods 1-3 do not, such as:

- lower benign utility damage for the same attack reduction;
- finer localization with reproducible causal effects;
- successful repair when receiver-only localization fails;
- stable mediation evidence across held-out attacks;
- a better non-dominated security/utility/cost frontier.

---

# 6. Contribution hierarchy after the novelty stress test

AETHER uses **three primary contributions** and a small number of Phase 2 extensions. Do not present a long feature list as equal novelty.

## 6.1 Primary Contribution C1 — Distributed Internal Causal Mediation (DICM)

**Phase:** mandatory Phase 1.

AETHER defines an intervention-based methodology for representing and testing causal mechanisms that are distributed across two separate model executions and an explicit serialized message mediator.

The core object is the **Distributed Causal Mechanism Graph (DCMG)**:

`sender internal components -> message mediator units -> receiver internal components -> outcome`

The graph does not assert causal edges merely because components are correlated. Cross-boundary links are accepted only when predeclared interventions produce repeatable effects.

### What must be implemented

- paired clean/attack traces;
- sender and receiver activation capture;
- structured message capture with stable token/span/field identifiers;
- sender intervention + message regeneration;
- message patch/mask/replacement;
- receiver intervention while message is fixed;
- bridge-effect estimators;
- graph construction;
- compact search over candidate elements;
- held-out validation.

### What can be claimed if successful

> On the evaluated models/tasks, the proposed distributed internal-causal analysis identifies an intervention-supported sender-message-receiver mechanism that cannot be reduced to receiver-only or trace-only evidence without a measurable loss in localization or repair performance.

### What cannot be claimed

- universal mechanism discovery;
- global minimality;
- one neural circuit spanning the models;
- first cross-agent causal analysis.

## 6.2 Primary Contribution C2 — Bridge Verification Protocol (BVP)

**Phase:** mandatory Phase 1; methodological validation contribution.

The most important scientific risk is falsely drawing arrows from sender activations to message content or from message tokens to receiver activations. BVP makes the bridge itself an experimental object.

For each candidate sender component `a`, mediator unit `m`, receiver component `b`, and outcome `Y`, Phase 1 records three intervention families:

1. **sender-to-mediator test:** intervene on `a`, regenerate the sender message, measure the change in `m` and downstream `Y`;
2. **mediator-to-receiver test:** hold the sender run fixed, patch `m` to its clean/attacked counterfactual, rerun the receiver, measure changes in `b` and `Y`;
3. **receiver-to-outcome test:** hold the received message fixed, intervene on `b`, and measure `Y`.

A candidate distributed path is accepted only when the relevant links survive controls, repeated cases, and at least two intervention operators where practical.

### Why this matters

Trace-level causal methods can prove that replacing a whole message changes an outcome. Receiver-only mechanistic methods can prove that a downstream component matters. BVP tests whether these pieces form a coherent mediated chain rather than merely co-occurring.

### Publication-safe claim

> We operationalize and evaluate an explicit bridge-verification protocol for testing internal-to-message and message-to-internal mediation across separate agent executions. Whether this exact protocol is priority-novel remains subject to final full-text and citation-chain review; the paper’s defensible contribution is the method and evidence actually demonstrated.

This is still phrased as a method contribution, not a universal priority claim.

## 6.3 Primary Contribution C3 — Constrained Tri-Location Intervention Selection

**Phase:** Phase 1 demonstration, Phase 2 full-scale evaluation.

AETHER does not assume there is one correct repair location. It creates a predefined candidate set:

- sender-internal interventions;
- message-level interventions;
- receiver-internal interventions.

Using **validation data only**, AETHER identifies the non-dominated candidates under four separately reported objectives:

- attack reduction;
- benign utility retention;
- latency/extra-forward-pass cost;
- intervention footprint.

The locked test set is then used once for final comparison against:

- no defense;
- fixed whole-message repair/filter;
- fixed receiver intervention;
- trace-level causal repair/replay where reproducible;
- a fixed sender intervention.

### Publication-safe claim

> We test whether distributed internal causal evidence improves the held-out security-utility-cost frontier for choosing among sender-, message-, and receiver-level interventions.

If it does not, the defense contribution is dropped and C1/C2 remain the paper.

## 6.4 Evaluation Contribution E1 — Standardized causal-resolution ladder

**Phase:** mandatory Phase 1 experimental design; do not oversell as algorithmic novelty.

AETHER's evaluation deliberately spans four resolution levels on the same or closely matched failures:

1. black-box behavior;
2. trace/message causal attribution;
3. correlational internal signals;
4. internal causal intervention across both agent executions.

This design is valuable because it tells reviewers exactly what additional white-box complexity buys. The project should release the experiment manifests and evaluation scripts as an artifact.

## 6.5 Phase 2 Extension X1 — Cross-attack and cross-protocol mechanism stability

Test whether DCMG elements discovered under one attack family remain useful under another, for example:

- MCP metadata/tool poisoning;
- tool-output indirect prompt injection;
- A2A message tampering/cascading injection.

The scientific question is **mechanism stability**, not attack novelty.

## 6.6 Phase 2 Extension X2 — Heterogeneous-model distributed mechanisms

Phase 1 may use the same small model family for both agents to simplify instrumentation. Phase 2 should deliberately use different sender and receiver model families.

This is important because the DCMG formalism is supposed to survive different internal activation spaces by using the message as the explicit mediator.

## 6.7 Phase 2 Extension X3 — Persistent memory-mediated mechanisms

Use a known memory-poisoning attack family. Ask whether the distributed mechanism changes across sessions and whether the same validated intervention remains effective after the attacker stops injecting new content.

Memory poisoning itself is prior art; the contribution would be the internal cross-execution persistence analysis.

## 6.8 Phase 2 Extension X4 — Mechanism-gated intervention

Use a lightweight detector derived from the validated mechanism to decide when to apply the expensive intervention. Compare:

- always-on intervention;
- no intervention;
- mechanism-gated intervention.

Treat this as an efficiency/utility study, not as a new idea unless a separate prior-art search supports it.

## 6.9 Phase 2 Extension X5 — Quantization and model-update stability

Test whether the same mechanism/repair remains stable across:

- FP16/BF16 vs INT8/INT4 variants;
- a controlled post-deployment fine-tuning step;
- one additional model family.

Again, the scientific question is stability of the distributed mechanism, not "edge AI novelty."

## 6.10 High-risk stretch — mechanism-informed adaptive attack generation

Only after C1-C3 and the journal-scale evaluation are complete, test whether internal causal evidence can guide generation of new adversarial cases. RL/adaptive attack generation is already crowded, so this must remain a stretch and cannot be allowed to consume Phase 1 time.

## 6.11 Features explicitly classified as infrastructure or context

The following may be necessary engineering, but must not appear as headline novelty:

- Recon/Planner/Exploit/Debrief multi-agent red-team roles;
- MCP/A2A protocol use;
- tool poisoning;
- message tampering;
- memory poisoning;
- RL/PPO/GRPO in general;
- activation steering in general;
- self-healing/rollback in general;
- medical/IoMT domain;
- RAG/vector databases;
- dashboards;
- edge hardware;
- LLM-generated code.

---

# 7. Testable hypotheses

The project uses hypotheses that can fail. No hypothesis is converted into a novelty claim before the locked-test result exists.

## H1 — Distributed internal mediation provides incremental causal localization

**Independent variable:** explanation/localization method: (a) receiver-only mechanistic intervention, (b) activation/probe or attention-dependence baseline, (c) trace/message-level counterfactual attribution, (d) DCMG + BVP.  
**Dependent variables:** held-out causal effect captured, attacked-to-clean decision-gap recovery, specificity to the unsafe decision, compactness, and intervention/query cost.  
**Primary baseline:** the strongest receiver-only and trace/message-level methods that can be reproduced fairly.  
**Protocol:** use the same paired clean/attacked cases, frozen splits, candidate granularity, and matched or transparently normalized intervention budgets. Discovery/tuning occurs only on train/development cases.  
**Expected result:** DCMG/BVP provides a measurable gain on at least one predeclared causal-resolution metric without merely spending unbounded extra queries.  
**Falsification:** receiver-only or trace/message-level methods match or beat DCMG/BVP on held-out failures at comparable cost. In that case, the paper becomes a comparative negative/limitation study rather than claiming added causal resolution.

## H2 — The sender-to-message-to-receiver bridge is intervention-supported rather than correlational

**Independent variable:** targeted bridge intervention versus matched random/shuffled interventions.  
**Dependent variables:** sender-to-mediator effect, mediator-to-receiver effect, receiver-to-outcome effect, sign/direction consistency, and end-to-end outcome change.  
**Baselines/controls:** random matched-size sender components, shuffled clean/attack message pairing, whole-message replacement, receiver-only intervention, and at least two intervention operators where practical.  
**Protocol:** (1) intervene on a sender component and regenerate the message; (2) hold sender execution fixed and patch the mediator; (3) hold the received message fixed and intervene on the receiver.  
**Expected result:** candidate bridges produce repeatable effects substantially larger than matched controls and form a coherent mediated chain on held-out cases.  
**Falsification:** bridge effects are unstable, disappear under alternative intervention operators, or are no stronger than matched controls.

## H3 — Distributed evidence can improve constrained repair selection

**Independent variable:** intervention-selection strategy: no defense, fixed whole-message repair/filter, fixed receiver intervention, trace-level causal repair/replay where reproducible, and validation-selected sender/message/receiver candidate from DCMG evidence.  
**Dependent variables:** attack success reduction, benign utility retention, latency/additional forward passes, and intervention footprint.  
**Protocol:** generate candidate interventions on training/development data; choose only from the validation-set Pareto frontier; evaluate once on the locked test set. Preserve tied/non-dominated solutions rather than forcing a unique site.  
**Expected result:** the DCMG-informed selector contributes at least one held-out non-dominated operating point unavailable to fixed baselines.  
**Falsification:** fixed message/receiver or trace-level repair dominates the proposed selector, or attack reduction is obtained only by broadly suppressing useful behavior.

## H4 — Distributed causal evidence generalizes beyond discovery examples

**Independent variable:** evaluation distribution: discovery-family versus held-out paraphrases/attack family/protocol condition.  
**Dependent variables:** retained intervention effect, component/pathway stability under predeclared matching, susceptibility prediction, and repair transfer.  
**Baselines:** receiver-only mechanism, trace/message attribution, activation probe, random matched-size pathway.  
**Expected result:** at least part of the intervention-validated mechanism retains above-baseline predictive or explanatory value on a held-out condition.  
**Falsification:** effects collapse to chance or only reproduce the exact discovery prompts. A negative result is scientifically useful and must be reported.

## H5 — Complex search algorithms are justified only if they improve the quality–cost trade-off

**Independent variable:** DCMG search method: random, greedy, beam, and a mandatory RL/MechRL-style policy; hierarchical search remains Phase 2.
**Dependent variables:** causal-quality metric(s), compactness, number of intervention evaluations/forward passes, wall-clock time, and stability across seeds.  
**Protocol:** identical candidate graph and evaluation data, with equal or explicitly reported budgets.  
**Expected result:** a complex search method is retained only if it offers reproducible benefit over simpler search.  
**Falsification:** greedy/beam matches RL. If so, RL is reported as unnecessary for this setting and is not used as a headline method.

---

# 8. Threat model

## 8.1 Assets

A1. Correctness of the downstream trust/escalation decision.  
A2. Integrity of MCP tool descriptions and results.  
A3. Integrity of A2A messages.  
A4. Integrity of agent memory.  
A5. Model-internal trust reasoning state.  
A6. Availability and benign utility of the system.

## 8.2 Adversary classes

**T1 — Malicious MCP tool/server.** Controls tool metadata and/or returned content within the experimental setup.

**T2 — Compromised upstream agent input.** Causes Agent A to receive adversarial information and generate a misleading but syntactically valid A2A message.

**T3 — A2A message manipulator.** Alters message fields/content in controlled experiments.

**T4 — Memory poisoning adversary (Phase 2).** Inserts crafted memory records that influence future trust/tool selection.

## 8.3 White-box distinction

During the **attack phase**, the modeled adversary does not need white-box model access.

During the **research-analysis phase**, AETHER has white-box access to selected open-weight model activations. This is not an attacker capability. It is required to study the causal mechanism.

## 8.4 Out of scope

- real patient data;
- deployment against real hospitals;
- physical medical-device exploitation;
- malware deployment;
- credential theft;
- destructive cyber activity;
- zero-day vulnerability discovery in production systems;
- real-world unauthorized MCP servers.

All attacks run against local, controlled test infrastructure.

## 8.5 Baseline security posture

The target should not be intentionally ridiculous. It should use:

- valid protocol schemas;
- reasonable authentication simulation where relevant;
- input validation for malformed data;
- deterministic tool identities;
- no hidden backdoor placed just to make attacks succeed.

The research is about model trust failures under valid-looking adversarial inputs, not trivial protocol bugs.

---

# 9. Demonstration target

## 9.1 Why a medical/IoMT-style target remains useful

The medical setting provides a high-stakes but controllable trust decision. It gives meaning to false trust without requiring the team to build a clinical product.

The target must remain deliberately small.

## 9.2 Recommended Phase 1 pipeline

Use two primary agents:

### Agent A — Intake / Evidence Agent

Responsibilities:

- receive a synthetic patient/task case;
- call one or two MCP tools;
- summarize the evidence;
- send an A2A message to Agent B.

### Agent B — Diagnostic / Escalation Agent

Responsibilities:

- consume Agent A's message;
- call one additional MCP tool in the declared Agent-B tool-use condition;
- produce a constrained decision:
  - `ESCALATE`,
  - `DO_NOT_ESCALATE`,
  - confidence/logit proxy.

The binary decision makes attack success easy to label.

### Mandatory Phase 1 Agent C — Policy/Review Agent

Only add if needed in Phase 2. Phase 1 should not require three agents for the main claim.

## 9.3 Example controlled scenario

A synthetic case contains a high-risk ECG/vital pattern.

Benign tool description:

> Returns recent sensor measurements for the patient.

Poisoned description/result encourages the intake agent to underweight or reinterpret the high-risk signal.

Agent A produces a structured summary.

Agent B decides whether to escalate.

The experiment asks:

- which sender components encoded the poisoned trust?
- which message span carried the causal influence?
- which receiver components transformed that message into the unsafe decision?

## 9.4 Clinical-data discipline

The target should use:

- public/synthetic data only;
- no claim of clinical validity;
- no statement that the model is suitable for patient care;
- a decision task simple enough to evaluate deterministically.

The medical domain is a **test harness**.

---


# 10. Layered system architecture: preserve AETHER, add DCMG/BVP as the research layer

## 10.1 Architectural principle

The revised project is **not** "old AETHER versus new AETHER." It is:

```text
OLD/EXISTING AETHER CAPABILITIES
        = platform foundation

+

DCMG + BVP
        = new Phase 1 research layer

+

broader validation / robustness / recovery work
        = Phase 2 journal/patent expansion
```

The system can remain broad while the scientific claim stays narrow. Reviewers should be able to separate what is implemented as useful infrastructure from what is experimentally claimed as a contribution.

## 10.2 Full layered architecture

```text
+================================================================================+
|                              AETHER PLATFORM                                   |
+================================================================================+

LAYER 1 — TARGET / AGENT EXECUTION
    public/synthetic task or medical/IoMT-style case
            ↓
    MCP-enabled tool interaction
            ↓
    Sender Agent A
            ↓
    explicit serialized A2A/MessageEnvelope
            ↓
    Receiver Agent B
            ↓
    policy/review/escalation component
            ↓
    objective behavioral outcome

LAYER 2 — ADVERSARIAL TESTING
    standardized MCPTox/TAMAS-derived conditions
    + existing deterministic attack corpus
    + Recon → Planner → Exploit → Debrief orchestration
    + tool-description poisoning
    + tool-output poisoning
    + A2A/message tampering
    + later memory/replay/spoofing/cross-protocol attacks

LAYER 3 — OBSERVABILITY / PROVENANCE
    run traces
    tool-call traces
    exact serialized messages
    attack metadata
    activation capture
    attention/head/MLP/residual locations where supported
    model/data/config hashes
    deterministic replay metadata

LAYER 4 — EXISTING MECHANISTIC / ATTRIBUTION METHODS
    receiver-only activation patching
    receiver-only circuit/mechanism search
    activation/probe baselines
    trace/message counterfactual attribution
    random / greedy / beam search
    mandatory MechRL-style / RL search

LAYER 5 — NEW PHASE 1 RESEARCH ADD-ON
    sender internal candidates
            ↓
    explicit serialized message mediator
            ↓
    receiver internal candidates
            ↓
    behavioral outcome

    Bridge Verification Protocol (BVP)
        A. sender intervention → regenerate message
        B. mediator intervention → rerun receiver
        C. receiver intervention with message held fixed

    Distributed Causal Mechanism Graph (DCMG)
    matched negative/random controls
    held-out intervention validation

LAYER 6 — SEARCH / EXPLANATION
    candidate screening
    random baseline
    greedy search
    beam search
    mandatory RL baseline; primary-method status still depends on evidence
    compact mechanism under declared graph/operator/budget

LAYER 7 — REMEDIATION LIBRARY
    sender-side intervention
    message sanitization / field patching
    receiver activation intervention
    activation steering where justified
    tool blocking / policy gate
    replay / rollback / recovery
    human escalation

LAYER 8 — INTERVENTION SELECTION
    evaluate attack reduction
    + benign utility retention
    + latency
    + query/compute cost
    + intervention footprint
    → preserve non-dominated/Pareto-efficient candidates

LAYER 9 — STANDARDIZED EVALUATION
    BFCL — benign tool/function competence
    MCPTox — MCP poisoning anchor
    TAMAS — multi-agent adversarial anchor
    Tracr — mechanistic ground-truth calibration
    IOI / Greater-Than — canonical model-internal calibration
    AETHER paired sender/message/receiver artifact — exact new causal question
    Phase 2: AgentDojo / NARCBench / ACIArena / second model families
```

## 10.3 What is preserved from the earlier system design

| Earlier capability | Preserve? | Current role |
|---|---:|---|
| MCP integration | yes | realistic tool boundary and attack surface |
| A2A / explicit inter-agent communication | yes | causal mediator boundary |
| medical/IoMT demonstration | yes | high-stakes case-study harness, not novelty |
| deterministic attack corpus | yes | fast local development and regression testing |
| Recon/Planner/Exploit/Debrief red-team roles | yes, if working | attack generation/demo infrastructure; Phase 2 breadth |
| tool poisoning / message tampering | yes | standardized adversarial stimuli |
| activation capture | yes | required instrumentation |
| patching/ablation/intervention engine | yes | required causal machinery |
| receiver-only circuit discovery | yes | important baseline and platform diagnostic |
| random/greedy/beam search | yes | mandatory search baselines |
| MechRL-style/RL search | yes, mandatory Phase 1 | comparison method; headline status depends on evidence |
| activation steering | yes | one remediation candidate |
| rollback/replay/recovery | yes | remediation candidate / system feature |
| remediation selector | yes | upgraded to constrained tri-location/Pareto evaluation |
| memory poisoning | yes, later | Phase 2 attack/generalization track |
| quantization/edge support | yes, later | Phase 2 robustness/deployment ablation |
| UI/dashboard | preserve if already useful | demo/observability only; cannot delay experiments |

## 10.4 Add-on interface contract

The DCMG/BVP layer should consume artifacts produced by the existing platform rather than forcing the whole repository to be rewritten.

Minimum inputs:

- `RunTrace` — one complete execution with provenance;
- `MessageEnvelope` — exact serialized agent-to-agent mediator;
- `AttackSpec` — controlled adversarial condition;
- `ActivationTrace` — sender/receiver internal values and hook metadata;
- `OutcomeRecord` — deterministic or predeclared behavioral endpoint;
- `InterventionSpec` — exact do/patch/ablation operation.

Minimum outputs:

- candidate sender/message/receiver nodes;
- bridge-test evidence for each accepted edge;
- DCMG artifact with provenance;
- matched controls;
- causal effect estimates;
- compact-mechanism search record;
- candidate remediation set;
- validation-set Pareto frontier;
- locked-test evaluation record.

This interface-first design allows the broader platform to evolve without invalidating the scientific method.

## 10.5 Capability is not novelty

The system may legitimately demonstrate many features. The paper must only claim novelty where the experiment supports it.

Examples:

- AETHER may **perform MCP tool poisoning**, but tool poisoning is prior art.
- AETHER may **run red-team agents**, but multi-agent red teaming is prior art.
- AETHER may **run MechRL-style search**, but RL circuit discovery is prior art.
- AETHER may **apply activation steering**, but steering is prior art.
- AETHER may **rollback/replay a workflow**, but recovery is prior art.
- AETHER may **combine these with DCMG/BVP**, but the scientific claim is the measured incremental value of the intervention-based distributed causal layer, not the fact that the technologies coexist.

## 10.6 Phase 1 versus Phase 2 architecture use

### Phase 1 must fully validate

- two-agent target and explicit mediator;
- standardized attack/benign anchors;
- activation capture/intervention engine;
- receiver-only and trace/message baselines;
- DCMG/BVP add-on;
- matched controls and held-out validation;
- sender/message/receiver remediation comparison;
- reproducibility and statistics.

### Phase 1 may preserve/demo without making it paper-critical

- existing red-team orchestration;
- medical UI;
- existing synthetic attack/search demos;
- steering/replay features not selected for the main comparison.

### Phase 2 expands

- attack breadth and adaptive red teaming;
- memory-mediated persistence;
- cross-protocol and heterogeneous-model mechanisms;
- ACIArena/AgentDojo/NARCBench-scale validation;
- query-efficient/hierarchical search;
- quantization/model-update stability;
- mechanism-gated recovery/self-healing;
- patent-oriented technical-effect evidence.

## 10.7 Keep protocol realism separate from methodological validity

The project should run real MCP/A2A reference SDKs where feasible, but the causal method must not depend on protocol branding. The core causal engine accepts a generic `MessageEnvelope` abstraction, allowing the same DCMG/BVP method to operate on A2A messages, ordinary JSON communication in standardized MAS benchmarks, replayed benchmark traces, and the medical demonstration harness.

This separation makes the architecture stronger: the existing AETHER platform remains useful, while the paper can test a protocol-agnostic causal methodology on standardized evidence.

---

# 11. Formal representation: Distributed Causal Mechanism Graph (DCMG)

## 11.1 Heterogeneous graph definition

For one paired clean/attacked execution, define:

`G_D = (V_A ∪ V_M ∪ V_B ∪ {Y}, E_A ∪ E_AM ∪ E_MB ∪ E_B)`

where:

- `V_A` = candidate sender-internal elements;
- `V_M` = explicit mediator units from the serialized message;
- `V_B` = candidate receiver-internal elements;
- `Y` = behavioral outcome;
- `E_A`, `E_B` = intra-model candidate dependencies;
- `E_AM` = empirically tested sender-to-message mediation links;
- `E_MB` = empirically tested message-to-receiver links.

Candidate internal elements may be attention heads, MLP blocks, residual-stream sites, selected token positions, or a small set of SAE features. Phase 1 should prefer coarse, auditable units over neuron-level scale.

Mediator units may be:

- JSON fields;
- tool/result fields;
- provenance labels;
- sentence spans;
- tokenizer-aligned spans;
- individual tokens only when span/field-level localization is stable.

## 11.2 Outcome and paired attack effect

Prefer deterministic or scalar outcomes. Let `s(x)` be a scalar unsafe-target score such as a target logit difference, unsafe action probability, or exact binary success indicator.

For a paired clean/attacked case `i`:

`Delta_i = s_i(attacked) - s_i(clean)`

All bridge and mechanism measurements should be related back to this paired attack effect.

## 11.3 Cross-boundary edges are not assumed from correlation

A sender component `a` is not connected to mediator unit `m` because attention is high or because their activations correlate. The edge is supported only when intervention on `a` changes `m` under a predeclared replay procedure.

Likewise, a mediator unit `m` is not connected to receiver component `b` merely because `b` activates after `m` is read. The link requires a message intervention that changes `b` and/or the outcome while relevant context is controlled.

## 11.4 Bridge Verification Protocol

### Test A — sender -> mediator

For a clean/attacked pair:

1. run the attacked sender and record activation `a_adv` and message `M_adv`;
2. patch/ablate candidate sender component `a` using a clean or matched-control value;
3. regenerate the message under the same decoding protocol;
4. compute change in mediator unit `m` and downstream outcome;
5. repeat across cases/seeds where stochastic generation is used.

Record:

- sender intervention operator;
- semantic/message difference;
- exact changed fields/spans;
- downstream effect.

### Test B — mediator -> receiver

1. keep the attacked sender trace fixed;
2. replace only candidate message unit `m` with its clean twin or controlled alternative;
3. run the same receiver checkpoint with fixed decoding configuration;
4. record changes in receiver components and outcome.

### Test C — receiver -> outcome

1. keep the received message fixed;
2. intervene on candidate receiver component `b`;
3. measure change in `Y`.

### Chain acceptance rule

A candidate path `a -> m -> b -> Y` can be described as **intervention-supported** only if all required component links pass the declared effect-size/stability threshold on validation data and survive negative controls.

## 11.5 Negative controls

At minimum include:

- random matched-size sender components;
- message spans unrelated to the manipulated evidence;
- random matched-size receiver components;
- shuffled clean donors for activation patching;
- same intervention on benign cases;
- message patch that preserves semantic content but changes irrelevant formatting where possible.

## 11.6 Candidate compact mechanism

Let `C ⊆ G_D` be the set returned by a search method. Phase 1 may describe `C` as a **candidate compact distributed causal mechanism** when it satisfies predeclared criteria for:

- causal effect recovery/removal;
- stability;
- benign specificity;
- compactness under the candidate graph.

Do not call `C` globally minimal. If every single allowed element removal from `C` breaks the validation threshold, report **one-step local minimality**.

## 11.7 Common evaluation quantity: causal effect recovery/removal

For an explanatory intervention set `C`, define a normalized recovery/removal score against the full paired attack effect. One permissible family is:

`CER(C) = 1 - |Delta_full - Delta_C| / (|Delta_full| + epsilon)`

The exact `Delta_C` depends on whether the experiment reconstructs the attacked effect or removes it; the paper must state the direction consistently and use the same definition across comparable methods.

Do not hide behind one custom scalar. Always report raw task/attack outcomes alongside CER.

---

# 12. Discovery/search methods and the role of RL

The paper must be valid even if RL is unnecessary. Implement methods in increasing complexity.

## 12.1 B0 — random matched-size search

Mandatory sanity control. Sample candidate elements while preserving approximate node-type counts and compare causal effect and benign damage.

## 12.2 B1 — greedy intervention search

Starting from a screened candidate set, iteratively remove the least important element while the validation constraint remains satisfied. This is the Phase 1 default because it is transparent and easy to audit.

## 12.3 B2 — beam search

Use when interactions make greedy search unstable. Maintain the top `B` candidate masks under the validation objective and fixed query budget.

## 12.4 B3 — receiver-only mechanistic search

Run the same search/intervention machinery on `V_B` only. This is a mandatory closest-method baseline because the paper's central claim is incremental value beyond the receiver.

## 12.5 B4 — MechRL-style single-model RL baseline

If resources allow, reproduce a simplified MechRL-style intervention environment on a canonical task first, then apply it to the receiver-only candidate set. Match intervention/query budget to other search methods.

## 12.6 Proposed heterogeneous DCMG search

The proposed search can operate over `V_A ∪ V_M ∪ V_B`. Phase 1 should use greedy or beam search unless the RL implementation is demonstrably stable.

If RL is used, action semantics must be typed:

1. select region: sender / mediator / receiver;
2. select candidate element;
3. apply prune/intervention/test/stop.

A possible validation reward is:

`R = lambda_effect * CausalEffect - lambda_benign * BenignDamage - lambda_size * SizePenalty - lambda_cost * InterventionCost`

But the paper must separately report each term and ablate the reward. A weighted reward score itself is not a scientific endpoint.

## 12.7 Decision rule about RL

By the Phase 1 feature freeze:

- if greedy/beam equals or beats RL at matched cost, use greedy/beam as the main method and report that RL was unnecessary;
- if RL clearly improves search efficiency or held-out results, report it as a search implementation contribution;
- never make the paper depend on forcing an RL result because "RL" is in the project history.

---

# 13. Causal intervention library

The intervention library is the scientific core. Every causal claim must map to an executable intervention.

## 13.1 Internal interventions

Required Phase 1 operators:

- activation patching from paired clean -> attacked run;
- mean or resample ablation from a matched clean/control distribution;
- zero ablation as an efficiency/sensitivity baseline.

Mandatory Phase 1 advanced operators:

- path patching;
- residual-stream patching;
- head-output patching;
- selected SAE-feature interventions.

## 13.2 Message interventions

Required:

- full clean-message patch;
- structured-field patch for JSON/A2A data;
- span patch for natural-language evidence;
- delete/neutralize implicated span;
- provenance-field patch where the protocol exposes provenance.

Important: a whole-message replacement is a strong coarse baseline, not evidence of fine-grained localization.

## 13.3 Replay discipline

Every intervention must specify what is held fixed and what is regenerated. Save:

- source and donor run IDs;
- exact prompt/context;
- model/tokenizer revisions;
- decoding parameters and seed;
- intervention operator and tensor location;
- original and intervened messages;
- outputs and scalar metrics.

## 13.4 Stochasticity handling

Where exact deterministic replay is impossible, use repeated forward replays and estimate an average causal effect with confidence intervals. Do not compare one lucky stochastic rerun with one unlucky baseline.

---

# 14. Constrained tri-location remediation

## 14.1 Candidate set

AETHER evaluates—not assumes—the following repair families:

- `S`: sender-internal patch/steer/ablation;
- `M`: message-level patch/filter/provenance correction;
- `R`: receiver-internal patch/steer/ablation.

## 14.2 No unique repair assumption

DoVer and related work show that several interventions may repair one failure. Therefore AETHER reports the **set of non-dominated interventions** rather than inventing a single canonical repair location.

## 14.3 Validation-set selection

For each candidate `i`, record separately:

- post-intervention attack success/effect;
- benign task utility;
- latency;
- extra forward passes;
- modified internal components;
- modified message fields/tokens;
- failure/refusal rate.

A candidate is eligible only if it satisfies a predeclared security threshold and benign-utility floor on validation data. Among eligible candidates, preserve the entire Pareto frontier.

## 14.4 Locked-test comparison

The final test must include at least:

1. no defense;
2. whole-message or fixed-message defense;
3. fixed receiver intervention;
4. DCMG-selected non-dominated intervention(s).

Where reproducible within the schedule, also include:

- trace-level causal repair/replay;
- fixed sender intervention;
- attention/probe-guided intervention.

## 14.5 Defense claim gate

AETHER may claim mechanism-informed intervention value only if the locked test shows a meaningful advantage after accounting for benign utility and cost. Otherwise, report the intervention experiment as negative/neutral and keep the paper focused on causal localization.

---

# 15. Attack corpus

## 15.1 Phase 1 attack families

Start with three controlled classes.

### A1 — Explicit MCP tool-description poisoning

Malicious instruction or misleading priority in tool metadata.

### A2 — Tool-output poisoning

Tool returns adversarial but syntactically valid content.

### A3 — A2A message tampering / agent-message manipulation

Structured field or evidence statement altered before receiver consumption.

## 15.2 Mandatory Phase 1 fourth class

### A4 — Implicit preference manipulation

No explicit malicious command; metadata wording biases selection/trust.

This is useful because it is less trivially detectable.

## 15.3 Phase 2 attack families

- persistent memory poisoning;
- Agent Card manipulation where technically relevant;
- cross-protocol variants targeting same decision;
- replay/context manipulation;
- multi-turn gradual poisoning;
- attacks generated through circuit-guided search only if core is stable.

## 15.4 Corpus schema

Each attack case should include:

```json
{
  "attack_id": "mcp_explicit_0001",
  "family": "mcp_tool_description_poisoning",
  "target_behavior": "suppress_escalation",
  "clean_case_id": "case_0042",
  "attack_surface": "tool_description",
  "attacker_goal": "DO_NOT_ESCALATE",
  "clean_payload": "...",
  "adversarial_payload": "...",
  "expected_safe_decision": "ESCALATE",
  "notes": "...",
  "source": "project_constructed_or_mcptox_adapted",
  "split": "train|validation|test"
}
```

## 15.5 Data leakage rule

The held-out attack set must be frozen before final circuit-generalization experiments. Do not repeatedly redesign attacks after seeing test results.

---


# 16. Models, standardized datasets, benchmark backbone, and compute

This section is binding. The project must separate **established external benchmarks** from **AETHER-created transformations/artifacts**. No adapted benchmark score may be reported as though it were the official benchmark.

## 16.1 Four-layer evidence stack

A reviewer should be able to trace each claim to an appropriate evidence source.

### Layer A — established external behavioral/security benchmarks

Use official or pinned releases without semantic modification when reporting benchmark scores.

**Mandatory Phase 1 external anchors:**

1. **MCPTox (AAAI 2026)** — standardized MCP metadata/tool-poisoning robustness.
2. **TAMAS (ACL 2026)** — standardized multi-agent adversarial robustness with 300 adversarial instances, six attack types, 211 tools, five scenarios, and 100 harmless tasks.
3. **BFCL (ICML 2025; pinned evaluator/tooling)** — benign tool/function-calling competence.

**Mandatory Phase 1 external cross-check:**

4. **AgentDojo (NeurIPS 2024)** — tool-using agent robustness to untrusted data/prompt injection; 97 realistic tasks and 629 security cases in the published benchmark.

**Phase 2 generalization anchor:**

5. **ACIArena (ACL 2026)** — 1,356 agent-cascading-injection test cases across multiple attack surfaces/objectives and six MAS implementations.

### Layer B — established mechanistic/interpretability calibration tasks

Use these to prove that the intervention/discovery code works before interpreting AETHER results.

1. **Tracr (NeurIPS 2023)** — compiled transformer models with known structure, explicitly intended as interpretability ground truth.
2. **GPT-2 Small IOI and/or Greater-Than** — canonical circuit tasks with published mechanistic structure.
3. **NARCBench released code/data** — multi-agent activation-probe baseline; not ground-truth causality, but important for reproducing the correlational multi-agent interpretability layer.

### Layer C — standardized source tasks transformed by a frozen AETHER adapter

AETHER may construct distributed-mechanism paired clean/attack tasks from standard source datasets, but these must be clearly labeled **adaptations/project artifacts**, never official benchmark cases.

Recommended Phase 1 sources:

- a deterministic subset of **MMLU** and/or **CommonsenseQA** for objective answer labels and inexpensive multi-agent evidence transfer;
- **PTB-XL v1.0.3** for the medical/IoMT case study, using PhysioNet's recommended patient-respecting folds.

The AETHER adapter must be deterministic, versioned, and published. Results on this layer are **AETHER benchmark results**, not official MMLU/CSQA/PTB-XL benchmark scores unless the original protocol is preserved exactly.

### Layer D — synthetic planted-causality microbenchmarks

Use Tracr or a small explicitly constructed two-execution transformer/message system with known planted causal components. This is the only layer where true internal ground-truth recovery can be measured directly.

Synthetic data is for **method validation**, not for the headline real-world security claim.

## 16.2 Mandatory external benchmark — MCPTox

### Why it is used

MCPTox anchors the project to a peer-reviewed MCP poisoning benchmark rather than a hand-written attack demo.

### Version/count discipline

The final AAAI 2026 article reports 1,348 generated malicious cases over 45 servers and 353 tools. The current public benchmark/Inspect implementation exposes 1,312 valid instances after excluding 36 records flagged as invalid. Therefore every AETHER report must include:

- paper citation;
- repository URL;
- exact git commit/release;
- exact valid-case count loaded by the evaluator;
- SHA256 of the frozen manifest.

Do not merge the 1,348 paper count and 1,312 valid-repository count into one number.

### Phase 1 use

- run the official/pinned benchmark protocol on the chosen Phase 1 agent model where feasible;
- report the official-compatible score separately;
- select a deterministic, stratified subset for expensive white-box instrumentation if the full benchmark is too costly;
- never call a custom two-agent transformation "the MCPTox score."

## 16.3 Mandatory standardized multi-agent benchmark — TAMAS

TAMAS is the preferred Phase 1 multi-agent external anchor because it is peer-reviewed at ACL 2026, has a public code/dataset release, includes harmless tasks as a utility control, and is materially smaller than ACIArena.

### Phase 1 minimum

- reproduce at least one published-compatible TAMAS configuration or a clearly documented subset using the official code;
- record task success/robustness metrics using official definitions;
- use selected traces to test AETHER logging/adapters;
- if white-box activation capture is incompatible with the original closed model configuration, rerun the same benchmark tasks with an open-weight model and label the results **AETHER open-model reproduction**, not official TAMAS numbers.

### Why this matters

TAMAS protects the paper from the criticism that the entire multi-agent attack surface was invented specifically for AETHER.

## 16.4 Phase 2 external generalization benchmark — ACIArena

ACIArena is a strong Phase 2 target because it covers 1,356 cascading-injection cases across multiple surfaces/objectives and six MAS implementations.

The Phase 2 journal should use ACIArena to ask whether DICM/DCMG conclusions survive:

- different MAS architectures;
- inter-agent message injection;
- different attack objectives;
- a benchmark the AETHER team did not design.

Do not promise full ACIArena completion for the November Phase 1 paper unless the core method is already frozen.

## 16.5 Mandatory benign tool-use benchmark — BFCL

A security result is unconvincing if the model cannot use tools correctly in benign conditions.

Use a pinned BFCL evaluator version/commit. At the time of this design pass, the BFCL leaderboard exposes reproducibility information for a pinned code/evaluator release; record the exact version actually used by the project.

Phase 1 should report:

- selected official-compatible categories;
- overall benign tool-call accuracy on those categories;
- malformed-call rate;
- abstention behavior where applicable.

Do not silently change tool schemas or scoring rules and continue calling the result BFCL.

## 16.6 AgentDojo as an external security/utility cross-check

AgentDojo is a NeurIPS 2024 Datasets & Benchmarks framework with 97 realistic tasks and 629 security test cases in the published version.

Phase 1: mandatory external security/utility cross-check, scheduled after the dependency-gating benchmark foundations.

Phase 2: recommended external cross-check for indirect prompt injection and utility preservation.

## 16.7 Tracr ground-truth calibration

Before AETHER claims internal causal localization on natural-language models, the intervention engine must succeed on at least one Tracr-compiled model with known structure.

Required outputs:

- candidate graph;
- discovered elements;
- precision/recall/F1 against known relevant structure where mapping is possible;
- effect of ablation/patching;
- random matched-size comparison.

## 16.8 Canonical GPT-2 Small circuit calibration

Reproduce at least one established behavior such as IOI or Greater-Than using published-compatible data generation and intervention definitions.

This is not AETHER novelty. It is an implementation sanity check proving the code can recover a known mechanism before being trusted on a new one.

## 16.9 NARCBench baseline

NARCBench is used for a specific purpose: reproduce a **correlational multi-agent activation baseline**.

Phase 1 options:

- run released probes on released activations/data;
- implement the same class of linear/probe aggregation on AETHER traces.

The paper must explicitly distinguish probe predictiveness from causal effect.

## 16.10 Standardized source task for the distributed mechanism experiment

The primary DCMG experiment must not rely solely on a custom medical task.

Use at least one objective-label source such as:

- MMLU subset;
- CommonsenseQA;
- another stable, open multiple-choice/structured benchmark approved before experiment freeze.

A recommended two-agent construction is:

1. Sender Agent A receives tool/evidence context and produces a structured evidence message;
2. Receiver Agent B answers the objective task using the message;
3. the attack modifies only the declared untrusted input/tool/message condition;
4. correctness is determined by the original dataset label, not an LLM judge.

This provides a clean scientific core with unambiguous ground truth.

## 16.11 PTB-XL v1.0.3 medical case study

PTB-XL remains useful as the medical demonstration source because PhysioNet provides patient-respecting stratified folds and recommends folds 1-8 for training, 9 for validation, and 10 for testing.

Use the medical pipeline as a **case study**, not the only evidence for the method and not a clinical claim.

Rules:

- pin PTB-XL v1.0.3;
- preserve patient-level fold separation;
- use only labels needed for a simple deterministic task;
- do not invent clinician-severity scores for the primary paper endpoint;
- state that the system is research software, not a medical device.

## 16.12 AETHER-created artifact: DCMG-Bench / AETHER-BridgeBench

The team may release a paired activation/message artifact for reproducibility. It must be called a **project benchmark/artifact**, not a standardized benchmark.

Each example should contain:

```text
case_id
source_benchmark
source_version
source_example_id
clean_input_hash
attack_input_hash
sender_model_revision
receiver_model_revision
clean_message
attacked_message
outcome_clean
outcome_attacked
attack_family
activation_manifest_A
activation_manifest_B
candidate_graph_manifest
split
seed
```

No raw proprietary data or hidden benchmark test content may be redistributed in violation of licenses.

## 16.13 Model strategy for student compute

### Phase 1

Use one small open-weight instruction model that:

- is competent enough on the chosen tool/task subset;
- exposes all activations;
- fits on available 16-24 GB GPU hardware in FP16/BF16 or can be run layer-by-layer without losing intervention fidelity;
- is supported by Hugging Face hooks, NNsight, TransformerLens, or a similarly auditable framework.

Do not choose a larger model merely for prestige. A 1-3B model with reliable white-box access is scientifically preferable to a 7-70B model that prevents intervention experiments.

Where possible, use the **same model family for sender and receiver in Phase 1** to reduce engineering risk. Heterogeneous model families are a Phase 2 experiment.

### Phase 2

Add at least one second model family and, if resources allow, one 3-7B-scale model. Report all results by model rather than pooling incompatible checkpoints.

## 16.14 Compute budget discipline

The scarce resource is repeated causal forward passes, not generated code.

Recommended hierarchy:

1. CPU/local laptop: data prep, benchmark adapters, tests, metrics, manifests;
2. one shared 16-24 GB GPU: 1-3B activation capture/interventions;
3. temporary cloud GPU: final larger sweeps or second-model validation;
4. no training from scratch.

Use caching aggressively:

- cache tokenized inputs;
- cache clean/attacked baseline activations needed repeatedly;
- cache message-generation outputs when the intervention does not alter sender state;
- shard activation storage by case/layer;
- never save every tensor at every token if the research question only requires selected sites.

## 16.15 Immutable benchmark manifest

Before final testing create `benchmarks/manifest_phase1.json` containing for every external resource:

- canonical name;
- publication;
- source URL/DOI/arXiv;
- code repository;
- exact commit/tag/version;
- license status;
- downloaded file hashes;
- number of examples loaded;
- exclusions and reasons;
- exact subset IDs used for expensive white-box analysis.

The paper's reproducibility appendix should be generated from this manifest.

---

# 17. Evaluation constitution: reviewer-defensible causal evidence and anti-loophole rules

This section governs every result that can enter the paper. The goal is not to make the system look good; it is to make the result hard to dismiss.

## 17.1 Phase 1 primary endpoints

Freeze the following before final test access:

1. **Conditional attack success rate** on clean-correct eligible cases for the primary adversarial task;
2. **Bridge mediation success rate:** fraction of attacked cases for which the predeclared sender->message and message->receiver intervention tests both pass;
3. **Held-out causal effect / repair performance** of the proposed DCMG method compared with receiver-only and trace/message baselines;
4. **Benign utility retention** under the selected intervention;
5. **Pareto status** of AETHER-selected interventions over security, benign utility, latency, and intervention footprint.

Search compactness, probe AUROC, circuit size, graph visualizations, and qualitative case studies are secondary endpoints.

## 17.2 Primary comparison is incremental value, not absolute success

The headline question is:

> What does internal sender-message-receiver causal analysis add beyond methods that already exist?

Therefore every main result table must contain at least:

- receiver-only causal method;
- trace/message counterfactual causal baseline;
- correlational activation/attention baseline;
- proposed DCMG method.

AETHER cannot claim success merely because its own intervention reduces ASR.

## 17.3 Attack/utility metrics

Report separately:

- clean task accuracy/success;
- unconditional ASR;
- conditional ASR on clean-correct cases;
- refusal rate;
- malformed/error/timeout rate;
- official benchmark metric when using MCPTox/TAMAS/BFCL/AgentDojo;
- any AETHER-specific metric under a separate name.

Never count infrastructure failures as attack successes unless the benchmark protocol explicitly does so.

## 17.4 Causal bridge metrics

For each candidate bridge, estimate paired effects.

### Sender-to-message effect

Measure whether the sender intervention changes the implicated message unit. Report both exact structural changes and semantic/task-relevant changes.

### Message-to-outcome effect

Patch the mediator while holding the receiver setup fixed; report the paired shift in the unsafe outcome.

### Receiver-to-outcome effect

Intervene internally on the receiver while holding the message fixed.

### Bridge mediation success

A case passes only when the required links meet the predeclared direction/effect threshold and controls do not show comparable effects.

## 17.5 Mechanism quality without overclaiming minimality

Report:

- candidate elements before screening;
- retained sender components;
- retained mediator units;
- retained receiver components;
- intervention query count;
- causal effect recovery/removal;
- benign damage;
- seed stability;
- one-step local-minimality check if performed;
- matched-size random percentile.

Use **compact**, **sparse**, or **locally minimal under our procedure**. Do not use global minimality language.

## 17.6 Planted-ground-truth metrics

Only synthetic/Tracr-style tasks can support true internal localization accuracy.

Report:

- precision;
- recall;
- F1;
- bridge localization accuracy;
- false-positive/false-negative rates.

For real LLM tasks, use intervention evidence rather than pretending the unknown true mechanism is available.

## 17.7 Intervention operator sensitivity

At least two operators must support the headline internal causal finding where computationally practical:

- activation patching or resample/mean ablation as the primary operator;
- a second operator such as zero/mean/resample patching as sensitivity analysis.

If the claimed mechanism reverses completely under reasonable intervention choices, report that instability.

## 17.8 Budget matching

Search algorithms and baselines must be compared under declared budgets such as:

- number of forward passes;
- number of candidate interventions;
- GPU-seconds;
- maximum candidate elements examined.

Do not let the proposed method use 100x more interventions than the baseline and then attribute the gain to the algorithm.

## 17.9 Repair evaluation

Report the full held-out frontier rather than one weighted score:

- ASR / unsafe-effect reduction;
- clean utility retention;
- latency;
- extra forward passes;
- sender components modified;
- message tokens/fields modified;
- receiver components modified.

Allow tied and multiple non-dominated repairs.

## 17.10 Statistical protocol

- paired binary outcomes: McNemar test plus paired effect and 95% CI;
- paired continuous/logit effects: paired permutation test or Wilcoxon as appropriate;
- CIs: paired bootstrap for paired differences;
- multiple confirmatory comparisons: Holm correction;
- discovery/search: at least 5 seeds where feasible;
- report every frozen seed, including unstable failures;
- predeclare sample size/subset selection for expensive activation runs.

## 17.11 Locked-test and pre-registration discipline

Before viewing final test outputs, commit and tag:

`docs/EXPERIMENT_FREEZE_PHASE1.md`

containing:

- hypotheses;
- benchmark versions/commits;
- model revisions;
- exact task IDs;
- attack templates;
- candidate graph rules;
- screening thresholds;
- intervention operators;
- baselines;
- search budgets;
- statistical tests;
- primary tables/figures;
- inclusion/exclusion policy.

Any post-freeze change must be logged as a protocol deviation.

## 17.12 No LLM judge for primary truth when deterministic truth exists

Use official labels, exact tool calls, AST/execution checks, structured-state checks, or task answers whenever possible.

If MCPTox's official-compatible evaluator uses a model judge, report that benchmark score as specified, but do not reuse an LLM judge to define the DCMG causal endpoint when deterministic paired outcomes are available.

## 17.13 Reproducibility metadata

Every paper run must save:

```text
run_id
git_commit
dirty_worktree_flag
benchmark_manifest_hash
source_case_ids
model_revision_A
model_revision_B
tokenizer_revisions
prompt/template hashes
attack_config_hash
candidate_graph_config
intervention_operator
search_budget
all seeds
hardware/CUDA/driver
Python lock hash
raw outputs
raw messages
activation artifact manifest
summary metrics
```

All paper tables/figures must be generated from immutable result artifacts.

## 17.14 Required negative controls

The final paper must include, where applicable:

- matched-size random internal components;
- irrelevant message-span patches;
- shuffled clean donors;
- benign-case interventions;
- receiver-only analysis;
- whole-message patch;
- random search;
- no-defense condition.

## 17.15 Threats to validity that must be stated

- Phase 1 may use one small open model family;
- external benchmarks test adjacent behavior, while DCMG is a new evaluation layer;
- the medical harness is not clinical software;
- candidate graph screening can exclude true causes;
- intervention operators can create off-manifold states;
- message serialization/tokenization can affect mediation analysis;
- compactness is conditional on the candidate set and budget;
- a full-message intervention may solve a failure more simply than internal analysis;
- PropGuard/CASPIAN/DoVer/CAR/MindGuard/MCPFixGen are strong adjacent methods and full reproduction may be limited by code/compute;
- negative results are possible and must not be hidden.

---

# 18. Mandatory baseline ladder

A Phase 1 paper is not submission-ready without this ladder.

## B0 — Black-box behavior only

Official benchmark/task outcome; no attribution.

## B1 — Trace/message counterfactual baseline

Implement CAR-style step/message intervention or a reproducible simplified counterfactual replay that edits/replaces the suspected message and reruns forward.

Purpose: asks whether trace-level causality already solves the localization problem.

## B2 — Activation probe baseline

NARCBench-style linear/probe analysis on sender/receiver internal states.

Purpose: separates predictive internal evidence from causal evidence.

## B3 — Attention/decision-dependence baseline

A MindGuard-inspired attention-dependence score on the relevant tool/message decision when technically compatible.

Purpose: compares causal intervention to a cheaper internal attribution signal.

## B4 — Receiver-only activation patching/pruning

Use exactly the same receiver intervention library available to the proposed method.

Purpose: closest mechanistic baseline.

## B5 — Receiver-only MechRL-style search

Mandatory Phase 1 baseline. Instability or resource limits are reported outcomes, not grounds for omission.

## B6 — Whole-message intervention

Replace/filter the entire message with a clean/control counterpart.

Purpose: strong coarse causal/defense baseline. The proposed method should not hide from this simple alternative.

## B7 — Random matched-size distributed mechanism

Mandatory sanity control.

## B8 — Proposed DCMG search + Bridge Verification Protocol

The main method.

## B9 — Fixed receiver repair

Always repair the receiver at a predefined site/strategy.

## B10 — Fixed message repair

Always repair/filter the message.

## B11 — Validation-selected DCMG repair

Non-dominated sender/message/receiver candidate chosen without test leakage.

## B12 — PropGuard/CASPIAN/DoVer class of baseline

Phase 1: include a closest reproducible trace/state propagation baseline or direct published comparison when exact reproduction is infeasible.

Phase 2: full reproduction/adaptation of at least one close state/trace-level method is strongly recommended.

---

# 19. Required ablations

## ABL1 — remove sender internals

Tests whether the proposed method reduces to receiver/message analysis.

## ABL2 — remove explicit mediator nodes

Tests whether modeling the serialized message as an explicit causal object matters.

## ABL3 — remove receiver internals

Tests whether sender/message evidence alone is sufficient.

## ABL4 — correlation only

Replace intervention evidence with probe/attention scores.

## ABL5 — whole-message only

Tests whether expensive internal localization beats a coarse but effective message patch on utility/cost.

## ABL6 — random vs greedy vs beam

Determines whether sophisticated search is necessary.

## ABL7 — RL vs deterministic search

Mandatory; compare at matched query/compute budget.

## ABL8 — intervention operator

Patch vs mean/resample/zero ablation.

## ABL9 — candidate granularity

Layer vs head/MLP vs selected token sites as compute allows.

## ABL10 — discovery/test separation

Discover on one subset; evaluate bridge and repair on held-out cases.

## ABL11 — attack family

At least two adversarial channels by the final journal; Phase 1 may use one primary + one held-out family.

## ABL12 — model family

Mandatory Phase 2. Same-model pair vs heterogeneous-model pair.

---

# 20. Repository architecture

Recommended monorepo:

```text
aether/
├── AGENTS.md
├── PROJECT_STATE.md
├── RESEARCH_CONTRACT.md
├── pyproject.toml
├── README.md
├── configs/
│   ├── models/
│   ├── attacks/
│   ├── experiments/
│   └── logging/
├── contracts/
│   ├── case.py
│   ├── message.py
│   ├── attack.py
│   ├── trace.py
│   ├── activation.py
│   ├── intervention.py
│   └── result.py
├── target/
│   ├── agents/
│   ├── mcp/
│   ├── a2a/
│   ├── memory/
│   └── runner.py
├── attacks/
│   ├── corpus/
│   ├── adapters/
│   ├── templates/
│   ├── a2a/
│   └── runner.py
├── instrumentation/
│   ├── hooks/
│   ├── cache/
│   ├── token_alignment/
│   └── trace_capture.py
├── causal/
│   ├── interventions/
│   ├── metrics/
│   ├── candidate_graph/
│   ├── bridge/
│   └── validation/
├── discovery/
│   ├── random_baseline/
│   ├── greedy/
│   ├── beam/
│   └── rl/
├── remediation/
│   ├── candidates/
│   ├── selector/
│   ├── steering/
│   └── gating/
├── evaluation/
│   ├── attack_metrics.py
│   ├── circuit_metrics.py
│   ├── stats.py
│   └── plots.py
├── experiments/
│   ├── phase1/
│   ├── phase2/
│   └── manifests/
├── data/
│   ├── synthetic_cases/
│   ├── attack_cases/
│   └── splits/
├── results/
│   ├── raw/
│   ├── processed/
│   └── figures/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── regression/
├── docs/
│   ├── architecture/
│   ├── decisions/
│   ├── experiment_cards/
│   └── literature/
└── scripts/
    ├── setup_env.sh
    ├── smoke_test.sh
    ├── run_phase1_matrix.py
    └── reproduce_paper_figures.py
```

---

# 21. Frozen data contracts

The contracts directory is the most important collaboration boundary.

## 21.1 PatientCase

Minimum fields:

```python
case_id: str
features: dict
ground_truth_decision: str
metadata: dict
```

## 21.2 A2AMessageRecord

```python
message_id: str
run_id: str
sender: str
receiver: str
content_text: str
structured_payload: dict | None
token_ids_sender: list[int] | None
token_ids_receiver: list[int] | None
provenance: dict
```

## 21.3 AttackSpec

```python
attack_id: str
family: str
target_surface: str
target_behavior: str
clean_payload: object
adversarial_payload: object
metadata: dict
```

## 21.4 RunTrace

```python
run_id: str
case_id: str
attack_id: str | None
seed: int
model_ids: dict
messages: list[A2AMessageRecord]
tool_calls: list[dict]
final_decision: str
decision_score: float | None
attack_success: bool
artifact_paths: dict
```

## 21.5 ActivationTrace

```python
run_id: str
agent_id: str
model_id: str
component_granularity: str
component_ids: list[str]
tensor_artifact_path: str
token_map: dict
```

Store tensors outside JSON.

## 21.6 InterventionSpec

```python
intervention_id: str
run_id: str
location_type: "sender" | "message" | "receiver"
component_id: str
operator: str
source_run_id: str | None
parameters: dict
```

## 21.7 CircuitResult

```python
experiment_id: str
source_attack_ids: list[str]
nodes: list[dict]
edges: list[dict]
faithfulness: float
necessity: float | None
size: int
benign_damage: float
search_method: str
search_cost: dict
```

## 21.8 Schema rule

No team member changes a frozen field name without:

1. opening a schema-change issue;
2. updating fixtures;
3. updating version number;
4. getting one other member approval.

This prevents late integration collapse.

---


# 22. Module-by-module implementation specification

## M1 — Target Harness

**Owner Phase 1:** Member 1  
**Purpose:** produce repeatable benign and adversarial multi-agent behavior.

### Submodules

M1.1 synthetic case loader  
M1.2 Agent A  
M1.3 MCP client/server adapter  
M1.4 A2A message adapter  
M1.5 Agent B  
M1.6 deterministic decision parser  
M1.7 trace logger

### Acceptance tests

- 50 benign cases run without crash;
- decisions serialized in exact schema;
- same seed/model/config reproduces same deterministic path when decoding is deterministic;
- attack can be toggled by configuration;
- trace includes every tool call/message.

---

## M2 — Attack Corpus and Attack Runner

**Owner:** Member 2

### Submodules

M2.1 MCPTox reading notes/adaptation layer  
M2.2 explicit tool-description poison  
M2.3 tool-output poison  
M2.4 A2A message manipulation  
M2.5 attack success evaluator  
M2.6 train/validation/test splitter  
M2.7 attack benchmark CLI

### Acceptance tests

- clean and poisoned payload differ only at intended surface;
- every attack has target outcome;
- ASR can be computed from stored traces;
- corpus is versioned;
- held-out split is immutable after freeze.

---

## M3 — Instrumentation and Intervention Engine

**Owner:** Member 3

### Submodules

M3.1 model wrapper  
M3.2 activation hooks  
M3.3 cache  
M3.4 zero ablation  
M3.5 mean ablation  
M3.6 activation patch  
M3.7 logit/decision metric  
M3.8 single-agent causal ranking

### Acceptance tests

- hook does not change unmodified model output;
- zero ablation changes only requested component;
- patch uses tensor from expected source run;
- activation IDs map consistently to layers/heads;
- unit test on tiny synthetic transformer or known simple case.

---

## M4 — Distributed Causal Mechanism Graph and Localization

**Owner:** Member 4

### Submodules

M4.1 graph schema  
M4.2 sender candidate nodes  
M4.3 message nodes  
M4.4 receiver nodes  
M4.5 bridge estimation  
M4.6 greedy/beam DCMG search  
M4.7 visualization  
M4.8 distributed causal-quality checker

### Acceptance tests

- graph can load from two activation traces + one message;
- intervention can target each of the three regions;
- circuit result is serializable;
- message patch causes expected downstream re-run;
- random baseline works at matched circuit size.

---

## M5 — RL Discovery

**Primary owner:** Member 3  
**Secondary owner:** Member 4

### Phase 1 scope

- reproduce simple single-agent environment;
- implement stable reward;
- extend from receiver-only nodes to the full sender/message/receiver DCMG candidate set.

### Phase 2 scope

- hierarchical heterogeneous action space;
- multi-example training;
- transfer/generalization;
- reward ablations.

---

## M6 — Remediation Selector

**Primary owner:** Member 4  
**Secondary owner:** Member 1

### Phase 1

Enumerative candidate selection.

### Phase 2

Gating/steering/learned selector if justified.

---

## M7 — Evaluation and Statistics

**Primary owner:** Member 2  
**Secondary owner:** all members contribute experiment outputs.

### Required

- ASR calculation;
- bootstrap CI;
- paired comparisons;
- circuit metrics;
- figure generation;
- experiment manifest loader.

---

## M8 — Reproducibility and Paper Artifacts

**Rotating owner**

Every experiment must have:

```text
experiment_id
git_commit
config_hash
model_id
dataset_split_hash
random_seed
hardware
timestamp
raw_result_path
```

No figure may be manually edited in a way that changes data.

---

# 23. Phase 0 emergency sprint: 4–8 October 2026

The October 8 code review is an intermediate checkpoint. Disjoint work is acceptable, but every member must show actual measurable progress.

## 23.1 October 4 night — freeze contracts

All four members together:

1. create repository;
2. write `RESEARCH_CONTRACT.md`;
3. freeze the one-sentence identity;
4. create contracts;
5. create branch names;
6. create common fixtures;
7. select model candidate;
8. select initial synthetic case format;
9. create experiment ID convention;
10. create issue board.

Branches:

```text
m1/target-harness
m2/attack-corpus
m3/mech-interventions
m4/dcmg-localization
```

Do not merge large features during this sprint unless necessary.

---

## 23.2 Member 1 sprint — Target Harness

### October 5

- create synthetic case loader;
- implement Agent A stub;
- implement Agent B stub;
- define deterministic structured output;
- use mock MCP/A2A adapters if official SDK integration is slow;
- produce one benign run end-to-end.

### October 6

- integrate one actual MCP tool call if feasible;
- implement clean vs poisoned tool configuration;
- log full trace;
- run 20–50 benign/attacked cases.

### October 7

- stabilize;
- unit tests;
- CLI;
- plot clean vs attacked decision distribution;
- documentation;
- freeze demo command.

### October 8

Only bug fixes/rehearsal.

### Code-review deliverable

```bash
python -m target.runner --config configs/experiments/review_target.yaml
```

Output must show at least one benign and one attacked decision plus saved trace.

---

## 23.3 Member 2 sprint — Attack Corpus and Evaluation

### October 5

- study MCPTox attack structure;
- create project-local attack schema;
- implement 10–20 attack fixtures;
- implement evaluator.

### October 6

- expand to 3 attack families;
- build corpus runner against mock target if needed;
- create ASR table generator.

### October 7

- run first benchmark on available target outputs;
- bootstrap CI utility;
- make ASR plot;
- write corpus README;
- freeze train/val/test split format.

### October 8

Rehearse:

```bash
python -m attacks.runner --config configs/experiments/review_attack.yaml
```

---

## 23.4 Member 3 sprint — Mechanistic Instrumentation

### October 5

- load selected open model;
- build hook registry;
- capture layer/head activations;
- verify output unchanged.

### October 6

- zero ablation;
- mean ablation;
- activation patch;
- define trust/decision scalar;
- run causal ranking on a few examples.

### October 7

- random pruning baseline;
- greedy pruning baseline;
- faithfulness-size curve;
- cache activations;
- tests.

### October 8

Demo:

```bash
python -m experiments.phase1.single_agent_circuit_smoke
```

Show an actual component ablation changing the target score.

---

## 23.5 Member 4 sprint — Distributed Causal Mediation Substrate

### October 5

- implement graph classes;
- create sender/message/receiver node types;
- use fixtures without waiting for Member 1;
- serialize graph.

### October 6

- implement message patch intervention;
- implement sender/receiver placeholder intervention adapters;
- create bridge scoring interface.

### October 7

- implement simple greedy DCMG pruning/localization on fixture or real traces;
- graph visualization;
- intervention-location comparison table.

### October 8

Demo:

```bash
python -m experiments.phase1.cross_agent_smoke
```

Show that a message patch or node intervention changes the downstream target score.

---

## 23.6 What the team should show on October 8

Four short demonstrations:

1. working target;
2. attack benchmark;
3. causal ablation;
4. DCMG/BVP intervention pipeline.

Also show:

- common contracts;
- branch structure;
- first quantitative plots;
- next-stage plan.

The review should communicate that the research has been decomposed scientifically, not merely that a lot of code was generated.

---


# 24. Phase 1 schedule: 9 October – 16 November 2026

Phase 1 must end with a complete research story. Feature development should largely stop well before 16 November.

## Week 1: 9–15 October — first integration

### Team goal

Create first real path:

`attack -> Agent A -> A2A message -> Agent B -> trace -> activations`

### Member 1

- replace mocks with stable protocol adapters where practical;
- deterministic target behavior;
- 100-case benign regression;
- trace completeness.

### Member 2

- 50–100 attacks;
- clean twins;
- attack success labels;
- frozen corpus v0.1.

### Member 3

- activation pipeline on Agent B;
- receiver-only causal baselines;
- first faithful compact circuit.

### Member 4

- load real traces;
- explicit message nodes;
- first real sender-message-receiver bridge-verification experiment.

### Integration checkpoint — 15 October

Required:

- one end-to-end attacked trace with sender/receiver activations;
- one clean twin;
- one message patch;
- one receiver intervention.

---

## Week 2: 16–22 October — discovery methods

### Member 1

- stabilize generation;
- seed/config handling;
- A2A message metadata/provenance;
- integration tests.

### Member 2

- increase corpus diversity;
- held-out split freeze candidate;
- benchmark scripts;
- first complete ASR baseline.

### Member 3

- greedy discovery;
- random baseline;
- single-agent MechRL-style environment prototype;
- faithfulness definitions.

### Member 4

- DCMG greedy/beam search;
- sender/message/receiver ablation support;
- circuit visualization.

### Required result by 22 October

A graph discovered from at least several successful attack traces with a faithfulness-size curve.

---

## Week 3: 23–29 October — core experiment

### Freeze research choices

By 23 October:

- final model for Phase 1;
- final node granularity;
- final primary attack families;
- final faithfulness formula;
- final main baselines.

### Member 1

- no new target features;
- reliability only;
- speed/caching improvements.

### Member 2

- execute baseline experiment matrix;
- CI/statistics;
- error categorization.

### Member 3

- stabilize RL if viable;
- compare random/greedy/RL receiver-only;
- reward ablation smoke tests.

### Member 4

- compare receiver-only vs DCMG/BVP under matched budgets;
- intervention location study.

### Required result by 29 October

At least one draft main paper table.

---

## Week 4: 30 October – 5 November — held-out tests and ablations

This is the most important science week.

Run:

- held-out attacks;
- matched-size random circuits;
- DCMG/BVP vs receiver-only and trace/message-level baselines;
- message node ablation;
- intervention comparison;
- multi-seed experiments.

Paper writing begins now, not later.

Each member drafts their owned methods subsection and results notes.

---

## Week 5: 6–10 November — experiment freeze

### 6–7 November

Last allowed methodological changes.

### 8 November

**Feature freeze.**

No new architecture features after this date unless a critical bug invalidates results.

### 8–10 November

- full reruns;
- confidence intervals;
- plots;
- error analysis;
- limitations;
- reproducibility checks.

By the evening of 10 November:

- raw results frozen;
- tables frozen except formatting;
- primary figures frozen.

---

## Week 6: 11–16 November — final integration and paper

### 11 November

- merge release candidate;
- clean environment test;
- reproduce core results from fresh checkout.

### 12 November

- paper full draft;
- literature/novelty re-check;
- verify every claim.

### 13 November

- internal mock peer review;
- each member reviews one section they did not write;
- fix unsupported claims.

### 14 November

- presentation/demo freeze;
- final figures;
- architecture diagram;
- appendix.

### 15 November

- final rehearsal;
- backup demo videos;
- tag release `phase1-paper`.

### 16 November

Phase 1 review / submission-ready milestone.

---

# 25. Phase 1 minimum publishable package

The Phase 1 package must contain:

## 25.1 Artifact

- reproducible codebase;
- attack corpus;
- synthetic/public case generation;
- trace schema;
- intervention library;
- discovery algorithms;
- experiment configs;
- result reproduction script.

## 25.2 Core experiments

### E1 — Attack baseline

Report ASR by attack family.

### E2 — Receiver-only circuit discovery

Compare random, greedy, and RL if stable.

### E3 — Distributed causal mechanism discovery

Compare receiver-only vs sender+message+receiver.

### E4 — DCMG-informed intervention

Compare:
- no defense;
- fixed message intervention;
- fixed receiver intervention;
- DCMG/BVP-informed candidate.

## 25.3 Required ablations

At minimum:

- remove sender;
- remove message;
- random matched-size;
- one intervention-type comparison.

## 25.4 Required paper claims

Keep Phase 1 claims narrow:

1. We define a **Distributed Causal Mechanism Graph (DCMG)** that represents sender-internal candidates, a serialized message mediator, receiver-internal candidates, and a behaviorally defined trust-failure outcome without conflating the two model executions into one neural circuit.
2. We implement intervention-based localization over those node classes and compare it under matched budgets with receiver-only mechanistic analysis, activation/probe baselines, and trace/message counterfactual attribution.
3. We test the falsifiable hypothesis that DCMG analysis provides incremental held-out localization/faithfulness value beyond those baselines; this is a result to be earned, not assumed.
4. We use validation data to select a **non-dominated** intervention from a predefined sender/message/receiver candidate set, then test security benefit, benign-utility cost, latency, and intervention cost once on the locked test set.

Do not claim universal multi-agent security.

---

# 26. Four-person Phase 1 work split

The split is equalized by vertical responsibility, not line count.

## Person 1 — Target & Protocol Lead

Owns:

- target harness;
- MCP/A2A adapters;
- synthetic/public case layer;
- trace generation;
- message provenance;
- target reliability;
- performance/regression tests.

Paper ownership:

- target environment;
- system architecture;
- implementation details;
- threat model implementation.

Main Phase 1 success metric:

> Other members can reproduce clean/attacked traces without asking Person 1 for manual help.

---

## Person 2 — Attacks, Benchmark & Evaluation Lead

Owns:

- attack corpus;
- attack adapters;
- MCPTox-inspired mapping;
- A2A manipulations;
- attack success labels;
- split management;
- statistics;
- tables/plots.

Paper ownership:

- adversarial methodology;
- dataset/attack corpus;
- metrics;
- statistical analysis;
- attack results.

Main success metric:

> All claims are backed by reproducible experiment manifests and confidence intervals.

---

## Person 3 — Mechanistic Discovery & RL Lead

Owns:

- activation hooks;
- interventions;
- receiver-only baseline;
- random/greedy discovery;
- RL environment/policy;
- faithfulness computation;
- activation caching.

Paper ownership:

- single-agent baseline;
- discovery algorithms;
- RL formulation;
- causal intervention details.

Main success metric:

> The team can causally alter the trust outcome through precisely logged internal interventions.

---

## Person 4 — Distributed Mediation & Constrained Repair Lead

Owns:

- heterogeneous graph;
- message mediator representation;
- sender-message-receiver bridge;
- DCMG search and bridge-verification experiments;
- mechanism visualizations;
- intervention candidate selection;
- remediation comparison.

Paper ownership:

- main novelty section;
- distributed causal-mediation formalism;
- DCMG-informed intervention;
- core diagrams.

Main success metric:

> The final paper's headline experiment runs through Person 4's pipeline using outputs from Persons 1–3.

---

# 27. Merge and integration strategy

The team should not wait until 13 November for the first merge.

## 27.1 Branch rules

Each member works in their owned top-level directories.

No one modifies `contracts/` casually.

All PRs require:

- passing tests;
- no secrets;
- changelog summary;
- experiment impact note.

## 27.2 Integration branches

Use:

- `main` — stable;
- `integration/phase1` — cross-module integration;
- feature branches per member.

## 27.3 Merge checkpoints

### 8 October

Contracts and smoke artifacts only.

### 12–15 October

First pairwise integrations:

- P1 + P2: attack -> target;
- P3 + P4: interventions -> DCMG/BVP evidence.

### 19 October

P1/P2 output feeds P3 activation capture.

### 22 October

Full target -> activation/message capture -> DCMG/BVP.

### 29 October

Full experimental pipeline.

### 5 November

Release candidate 0.

### 11 November

Release candidate 1 / paper results freeze.

## 27.4 Interface-first rule

If another person's module is unavailable, use fixtures conforming to the contract.

Never block for more than half a day waiting on another member's implementation.

---

# 28. Instructions for coding agents and chatbots

The team has 2–3 coding agents/chatbots per person but limited tokens. AI use must be disciplined.

## 28.1 Do not ask an agent to "build AETHER"

That causes:

- duplicated architectures;
- undocumented assumptions;
- oversized changes;
- token waste;
- integration conflicts.

Every coding-agent task must be bounded.

## 28.2 Mandatory context files for agents

At repo root:

### `AGENTS.md`

Contains:
- coding style;
- prohibited directories;
- test commands;
- architecture invariants;
- no-schema-change rule;
- no hidden fallbacks;
- logging requirements.

### `RESEARCH_CONTRACT.md`

Contains:
- one-sentence project identity;
- what is novel;
- what is not novel;
- definitions of attack success, faithfulness, and circuit.

### `PROJECT_STATE.md`

Updated daily:
- completed;
- in progress;
- failing tests;
- known bugs;
- decisions;
- current experiment status.

### `TASK.md`

Temporary task-specific file:
- scope;
- exact files;
- acceptance tests;
- non-goals.

## 28.3 Standard coding-agent prompt

Use a prompt like:

> Read `AGENTS.md`, `RESEARCH_CONTRACT.md`, `PROJECT_STATE.md`, and this task specification completely before editing. Inspect the repository and tests. Implement only the requested module. Do not change public contracts or unrelated modules. Add/modify tests first where practical. Run the smallest relevant tests during iteration and the specified full test command before finishing. Do not fabricate experiment results. Do not silently catch errors or add fake fallback outputs. At the end, report changed files, tests run, remaining limitations, and any assumptions that need human review.

## 28.4 Reviewer-agent prompt

> Review this branch as a skeptical research software reviewer. Check for schema violations, hidden mock behavior, hard-coded values that could leak labels, invalid causal assumptions, non-determinism, missing seeds, data leakage, tests that only test mocks, and experiment code that cannot reproduce its figures. Do not rewrite the branch unless asked. Produce a prioritized issue list.

## 28.5 Debug-agent prompt

Give:
- exact error;
- command;
- relevant files;
- expected behavior.

Ask for:
- root cause;
- smallest fix;
- test preventing recurrence.

## 28.6 Token-budget rules

Use strongest coding agent for:

- multi-file implementation;
- architecture-sensitive changes;
- complex debugging;
- test-driven refactoring.

Use cheaper/faster chatbot for:

- README drafts;
- experiment-table formatting;
- docstrings;
- small helper functions;
- plotting suggestions;
- summarizing logs;
- literature note organization.

Human team members must make final decisions about:

- causal validity;
- novelty;
- metric definitions;
- experiment interpretation;
- claims in paper.

## 28.7 Never let agents fabricate results

No AI-generated number may enter the paper unless it came from an executed experiment and can be traced to a raw result file.

---

# 29. Experiment-management protocol

## 29.1 Experiment card

Every nontrivial experiment gets a Markdown/YAML card:

```yaml
experiment_id: P1_E3_2026-10-28_001
research_question: "Does DCMG/BVP add held-out causal localization beyond receiver-only and trace/message baselines?"
hypothesis: H1
git_commit: ...
config: ...
dataset_split: ...
model: ...
seeds: [1, 2, 3, 4, 5]
baselines:
  - receiver_greedy
  - cross_agent_greedy
metrics:
  - faithfulness
  - circuit_size
status: planned
```

After run:

```yaml
status: completed
raw_results: results/raw/...
figure_outputs: ...
notes: ...
```

## 29.2 Result immutability

Do not overwrite final raw results.

Use new experiment IDs.

## 29.3 Figure generation

All figures generated from scripts.

Example:

```bash
python -m evaluation.plots \
  --manifest experiments/manifests/main_results.yaml \
  --out results/figures
```

## 29.4 Seeds

During development: one fixed seed.

Final experiments: multiple seeds where stochasticity matters.

## 29.5 Hardware logs

Record GPU/CPU/RAM because intervention/search cost is part of feasibility.

---

# 30. Phase 1 paper structure

Proposed structure:

## Title

Avoid stuffing every technology into the title.

Candidate:

**AETHER: Intervention-Based Distributed Causal Localization of Adversarial Trust Failures in Tool-Using Multi-Agent Systems**

## Abstract

Four sentences:

1. problem;
2. gap;
3. method;
4. results/contribution.

## 1. Introduction

- multi-agent trust failures;
- black-box limitation;
- distributed causal-mediation question;
- contributions.

## 2. Related Work

- MCP attacks / MCPTox;
- circuit discovery / MechRL;
- security circuits;
- multi-agent interpretability;
- cross-agent causal monitoring.

## 3. Threat Model and Task

- target system;
- attack model;
- unsafe trust definition.

## 4. Method

- candidate graph;
- bridge representation;
- interventions;
- search;
- faithfulness;
- intervention selection.

## 5. Experimental Setup

- models;
- cases;
- attacks;
- baselines;
- metrics.

## 6. Results

- attack baseline;
- receiver-only discovery;
- distributed causal localization;
- interventions;
- ablations.

## 7. Discussion

- when distributed internal mediation adds value beyond simpler baselines;
- negative cases;
- limitations.

## 8. Conclusion

Narrow, evidence-based conclusion.

## Appendix

- schemas;
- hyperparameters;
- prompts;
- additional figures;
- experiment manifest.

---

# 31. Paper-writing ownership

Person 1:
- system/testbed;
- protocols;
- implementation.

Person 2:
- attacks;
- evaluation setup;
- statistics.

Person 3:
- circuit discovery;
- RL/baselines;
- intervention mechanics.

Person 4:
- distributed causal-mediation formalism;
- remediation;
- main novelty explanation.

Shared:
- abstract;
- introduction;
- related work;
- conclusion.

Final editor:
- rotate or choose one person with strongest academic writing.
- final editor may harmonize style but cannot change technical claims without owner review.

---


# 32. Phase 2: 17 November 2026 – April 2027

Phase 2 is not a feature-accumulation period. It exists to turn the strongest Phase 1 finding into a journal-grade, externally reproducible study and, only if a concrete technical mechanism survives a full prior-art audit, a patent-disclosure candidate.

The Phase 2 rule is:

> **Broaden evidence before broadening claims.**

A feature is admitted into Phase 2 only if it strengthens one of the following questions:

1. Does DCMG/BVP provide causal information that receiver-only, probe/attention, and trace/message-level approaches do not?
2. Does that additional information survive changes in attack, protocol, model, task, or time?
3. Can the information reduce the cost or collateral damage of a defensive intervention?
4. Can the method be made sufficiently reproducible and computationally efficient to be useful outside the original demonstration harness?

## 32.1 Phase 2 success criteria

By April 2027 the project should aim to have:

- the Phase 1 paper fully reproducible from a clean machine;
- all main claims rechecked against the then-current literature;
- at least one standardized external multi-agent benchmark beyond the Phase 1 minimum, preferably ACIArena and/or AgentDojo;
- at least two attack families and, if feasible, both MCP- and A2A-mediated failures;
- at least two open model families if compute permits;
- held-out and cross-domain/generalization tests rather than only rediscovery on the training scenario;
- a query/compute-budget analysis of the causal search;
- mechanism stability analysis across seeds and paraphrases;
- a complete security–utility–latency–intervention-footprint frontier;
- negative controls and failure cases;
- a replication package containing manifests, hashes, configs, code, seeds, results and figure-generation scripts;
- a journal-ready manuscript whose novelty wording is no broader than the evidence;
- a patent disclosure only if the executable technical procedure, not the broad idea, remains differentiable from prior art.

## 32.2 Phase 2 novelty-selection gate — 17–25 November

Immediately after Phase 1, the team must create a one-page **claim survival report** for every candidate extension. Each item receives one of four statuses:

- **Promote:** Phase 1 evidence supports it and prior art leaves a clear technical distinction.
- **Evaluate as RQ:** scientifically interesting, but not safe to call novel before experiments.
- **Context/ablation:** valuable evaluation, not a novelty.
- **Drop:** duplicates prior art or consumes disproportionate engineering effort.

No more than **three major Phase 2 extensions** may be promoted simultaneously.

Recommended default ordering if Phase 1 succeeds:

1. **X1 — Cross-attack / cross-protocol mechanism stability**;
2. **X2 — Heterogeneous-model, alignment-free mediation analysis**;
3. **X3 — Query-efficient hierarchical DCMG search** *or* **X4 — temporal/memory mediation**, depending on Phase 1 failure modes.

Constrained repair remains part of the main system, not a separate novelty unless the held-out frontier is demonstrably better than fixed and trace-level repair baselines.

If Phase 1 does **not** show incremental value over receiver-only or trace/message-level attribution, Phase 2 must not hide that result by adding features. The first task becomes diagnosing the failure and either (a) narrowing the scientific question, or (b) converting the project into a rigorous comparative study.

---

# 33. Phase 2 defensible extension portfolio

The following extensions are ordered by scientific defensibility, not by how impressive they sound.

## 33.1 X1 — Cross-attack and cross-protocol mechanism stability

### Question

When two structurally different attacks produce the same unsafe downstream trust decision, do they share any intervention-validated portion of the distributed mechanism?

### Examples

- MCP tool-description poisoning versus MCP tool-output poisoning;
- MCP-originated poisoning versus A2A message manipulation;
- direct single-turn manipulation versus paraphrased/semantically equivalent manipulation.

### Why it matters

A mechanism that exists only for one exact prompt is an incident explanation. A mechanism that predicts or localizes held-out failures is much more scientifically useful.

### What is *not* claimed

Cross-protocol transfer or generalization is not presumed novel. The contribution is the controlled empirical characterization of **distributed internal mechanism stability** under the specific DCMG/BVP formalism.

### Required experiment

Discover on one attack family using training/development data only. Freeze the candidate mechanism. Evaluate on a held-out family without rediscovery, then compare:

- effect-direction consistency;
- pathway overlap under predeclared matching rules;
- faithfulness/necessity retained on held-out cases;
- repair transfer;
- baseline transfer for receiver-only and trace-level methods.

A negative result is publishable and must be reported.

## 33.2 X2 — Heterogeneous-model, alignment-free mediation analysis

### Question

Can DCMG/BVP operate when sender and receiver use different model families without requiring direct alignment of their hidden spaces?

### Core idea

AETHER does not need to claim that a sender head "corresponds" to a receiver head. The message mediator supplies the causal interface. Effects are estimated separately:

`sender component -> message mediator`

and

`message mediator -> receiver component -> outcome`.

This makes the method naturally compatible with heterogeneous agents if the intervention semantics remain valid.

### Scientific value

This is stronger than a same-checkpoint two-agent demo because practical multi-agent systems are heterogeneous. It also tests whether the proposed causal object is genuinely protocol-mediated rather than an artifact of identical model internals.

### Claim discipline

Treat this as a research question until a fresh prior-art search specifically targeting heterogeneous internal causal attribution is complete.

## 33.3 X3 — Query-efficient hierarchical DCMG search

### Motivation

Full component-by-component intervention is expensive. A flat search can require too many forward passes even on small models.

### Proposed hierarchy

1. **trace-level localization:** identify relevant turn/message field/tool event;
2. **coarse internal screening:** layer/module/head groups;
3. **fine internal intervention:** only within surviving groups;
4. **bridge verification:** expensive BVP tests only for surviving sender/message/receiver candidates;
5. **compactness cleanup:** greedy/beam/RL pruning under a common budget.

### Novelty condition

The hierarchy is not novel merely because it is hierarchical. It becomes a defensible method contribution only if it achieves a predeclared causal-quality target with materially fewer interventions/forward passes than flat search under the same candidate space.

### Mandatory baselines

- random search;
- greedy search;
- beam search where tractable;
- MechRL-style search on the receiver-only graph;
- flat DCMG search on a small case where exhaustive or near-exhaustive comparison is possible.

## 33.4 X4 — Temporal / memory-mediated distributed mechanisms

### Question

For a memory-poisoning failure, can the causal chain be separated into:

`poisoned memory write -> later retrieved mediator/context -> receiver internal mechanism -> unsafe outcome`?

### Prior-art constraint

Memory poisoning itself is established prior art. Persistence itself is also well studied behaviorally. The only defensible contribution would be a controlled **internal causal mediation analysis of persistence** under the DCMG/BVP methodology.

### Required controls

- clean memory reset;
- matched benign persistent memory;
- poison write without retrieval;
- retrieval without poison;
- attack stopped after initial write;
- multiple later sessions;
- behavioral and internal causal metrics reported separately.

## 33.5 X5 — Mechanism-conditioned repair under distribution shift

Phase 1 tests whether distributed evidence can choose a non-dominated intervention on held-out cases. Phase 2 can ask whether that selection policy remains useful under attack paraphrase, new protocol surface, or second model family.

This is not a new steering primitive. The contribution, if any, is **selection robustness**: whether the same evidence-to-intervention rule continues to improve the security–utility–cost frontier compared with fixed repair.

## 33.6 X6 — Quantization / edge robustness as an ablation

Quantization is not a novelty claim. It is an engineering/scientific robustness question:

- do discovered causal effects survive INT8/low-bit deployment?
- does intervention ranking change?
- does quantization materially change faithfulness or search cost?

This is useful for the medical/edge demonstration but should remain an ablation unless results reveal a genuinely new phenomenon.

## 33.7 X7 — Adaptive attack generation from mechanism evidence — stretch only

This is high risk because RL-based attack generation and activation-guided attack construction are crowded areas. Do not include it in the core journal plan unless a dedicated prior-art search identifies a precise gap and all higher-priority work is complete.

---

# 34. Phase 2 month-by-month roadmap

## 34.1 Late November – December 2026: reproduce, audit, harden

### Research

- rerun every Phase 1 main experiment from a clean environment;
- complete the full-text audit of PropGuard, CASPIAN, NARCBench, DoVer, CAR, MindGuard, MCPFixGen, AttriGuard, AgentSentry, the multi-agent sycophancy/activation-patching work, and new citation descendants;
- construct claim charts showing exactly what each closest method does and does not do;
- perform error analysis on every Phase 1 failure case;
- determine whether DCMG's incremental gain comes from sender internals, mediator decomposition, receiver internals, or simply extra compute;
- rerun under matched intervention/query budgets where Phase 1 comparisons were imperfect.

### Standardized evaluation

- pin all Phase 1 benchmark versions permanently;
- reproduce at least one additional standardized benchmark configuration if resources permit;
- begin ACIArena compatibility work, but do not delay core reproduction for a large benchmark port.

### Engineering

- containerize the full experiment stack;
- build a stable experiment registry;
- cache deterministic activations and message artifacts with integrity hashes;
- add automatic manifest validation;
- create one-command reproduction targets for every main table/figure.

### Output by 31 December

- Phase 1 replication report;
- updated related-work/claim matrix;
- Phase 2 preregistered experiment plan;
- frozen choice of at most three Phase 2 extensions;
- patent go/no-go memo based on technical prior art, not enthusiasm.

## 34.2 January 2027: external generalization

Primary work:

- run ACIArena and/or AgentDojo compatible external evaluation where technically appropriate;
- add one second open model family if hardware allows;
- execute X1 cross-attack/cross-protocol held-out tests;
- execute X2 heterogeneous-model mediation pilot;
- reproduce NARCBench-style activation probes on an overlapping multi-agent setting where feasible;
- compare DCMG against the strongest implementable trace/message causal baseline.

By 31 January, there must be at least one result answering whether the Phase 1 causal finding survives a meaningful distribution change.

## 34.3 February 2027: efficiency and remediation robustness

Depending on the November gate, prioritize one:

- X3 hierarchical/query-efficient search; or
- X4 memory/persistence mediation.

In parallel:

- expand constrained tri-location intervention evaluation;
- report the complete Pareto frontier rather than one chosen operating point;
- test repair under paraphrase/new attack family;
- measure latency, extra forward passes, memory, and intervention footprint;
- run benign regression after every defense experiment.

Patent counsel/TBI engagement may proceed only if a concrete technical method still appears differentiable after the full-text audit.

## 34.4 March 2027: journal experiment freeze

By the first week of March, methodology and dataset versions freeze.

Run the final matrix with:

- standardized external security benchmark(s);
- AETHER paired clean/attacked distributed-mechanism artifact;
- at least two attack families;
- one or two model families depending on feasibility;
- receiver-only mechanistic baseline;
- activation/probe baseline;
- trace/message causal baseline;
- DCMG/BVP method;
- fixed and constrained repair baselines;
- multiple seeds/repeated paired cases;
- matched query/compute reporting;
- stability and sensitivity tests;
- negative controls.

Complete statistical analysis, error taxonomy, and reproducibility audit before drafting final conclusions.

## 34.5 April 2027: manuscript, artifact, patent decision

April is a no-new-feature month.

Required outputs:

- final journal manuscript;
- artifact README and dataset card;
- container/environment lock file;
- experiment manifests and hashes;
- scripts regenerating every main table/figure;
- final limitation section;
- final updated literature search;
- archival code release plan;
- final-year demo;
- patent disclosure only if institutional IP review approves the narrowly defined mechanism.

---

# 35. Phase 2 equal work split

The four-person split continues to follow vertical scientific ownership. Equal work means comparable responsibility and deliverables, not equal numbers of source files.

## Person 1 — Systems, Protocols & Reproducibility Lead

Owns:

- MCP/A2A target harness hardening;
- second target/model integration plumbing;
- multi-turn/persistent-memory environment if X4 is selected;
- external benchmark adapters that touch protocol execution;
- runtime/edge profiling;
- containers and fresh-machine reproduction.

Monthly evidence requirement:

- one merged systems milestone;
- one reproducibility or runtime result;
- one methods subsection/update;
- one cross-review.

## Person 2 — Benchmarks, Generalization & Statistics Lead

Owns:

- ACIArena/AgentDojo/TAMAS/MCPTox benchmark manifests;
- attack families and held-out splits;
- X1 cross-attack/cross-protocol tests;
- statistical analysis and confidence intervals;
- dataset cards and benchmark provenance;
- final figures/tables.

Monthly evidence requirement:

- one benchmark/result package;
- one statistical validation report;
- one results subsection;
- one cross-review.

## Person 3 — Internal Causality & Search-Efficiency Lead

Owns:

- sender/receiver intervention engine;
- receiver-only mechanistic baselines;
- random/greedy/beam/MechRL-style search comparisons;
- X3 hierarchical search if selected;
- intervention/query-cost accounting;
- mechanism stability and sensitivity analysis.

Monthly evidence requirement:

- one causal/search result;
- one baseline or ablation;
- one methods subsection;
- one cross-review.

## Person 4 — Distributed Mediation & Constrained Repair Lead

Owns:

- DCMG/BVP implementation and validation;
- X2 heterogeneous mediation if selected;
- tri-location intervention candidate generation;
- Pareto repair selection;
- distributed mechanism / bridge-evidence visualizations;
- technical material for any patent disclosure.

Monthly evidence requirement:

- one DCMG/repair result;
- one held-out or stability evaluation;
- one methods/results subsection;
- one cross-review.

## Phase 2 integration rule

At least once every two weeks the team must run one shared end-to-end experiment from a clean integration branch. No member may maintain an isolated research branch for more than fourteen days without merging an interface-compatible version.

---

# 36. Candidate Phase 2 contribution matrix

| Candidate | What it actually contributes | Scientific value | Engineering cost | Prior-art risk | Status rule |
|---|---|---:|---:|---:|---|
| X1 Cross-attack/cross-protocol mechanism stability | tests predictive/generalization value of DCMG | High | Medium | Medium | Promote if Phase 1 DCMG survives |
| X2 Heterogeneous-model alignment-free mediation | tests protocol-mediated causality without hidden-space alignment | High | Medium | Medium | Promote after targeted search |
| X3 Query-efficient hierarchical DCMG search | reduces intervention burden while preserving causal quality | High if successful | Medium | Medium | Claim only if efficiency gain is measured |
| X4 Temporal/memory mediation | internal causal account of persistent memory-borne failure | Medium-High | Medium | High | RQ unless literature gap verified |
| X5 Mechanism-conditioned repair under shift | tests repair-selection robustness | Medium-High | Medium | High | Evaluation contribution unless it beats close baselines |
| X6 Quantization/edge robustness | deployment robustness ablation | Medium | Low-Med | Low | Context/ablation |
| X7 Mechanism-informed adaptive attack generation | closes analysis-to-attack loop | Potentially high | High | Very high | Stretch/drop by default |

At most three X-items may appear as major journal contributions. More features usually weaken rather than strengthen the paper.

---

# 37. Patent and Q1-journal strategy after prior-art hardening

## 37.1 Patent strategy — extremely narrow by design

This section is research/IP planning, not legal advice or a patentability opinion.

### Broad concepts that are too crowded to treat as the invention

Do not draft the invention around:

- cross-agent causal attribution in general;
- propagation graphs;
- RL subgraph search;
- MCP/A2A security;
- tool poisoning;
- activation steering;
- counterfactual replay;
- rollback/self-healing;
- generic mechanism-guided remediation.

### Potentially differentiable technical procedure

If experiments and a professional prior-art search support it, the candidate technical procedure is much narrower:

> **An executable intervention protocol that localizes an adversarial trust failure across internal components of a first model execution, a serialized inter-agent mediator, and internal components of a second model execution, verifies the internal-to-mediator and mediator-to-internal bridges through controlled re-execution, and uses the resulting evidence to choose from a constrained set of sender/message/receiver interventions subject to explicit utility and execution-cost constraints.**

Even this is only a candidate. PropGuard, CASPIAN, CAR, DoVer, AttriGuard, AgentSentry, MindGuard, MCPFixGen and related patents/publications must be claim-charted in full before filing.

### Evidence that strengthens any IP disclosure

Preserve:

- exact graph/node semantics;
- intervention and replay semantics;
- bridge verification algorithm;
- query-efficiency procedure if X3 succeeds;
- technical effect measurements;
- security/utility/latency improvements over closest prior art;
- reproducible implementation details;
- dated commit history and inventor contributions;
- failed alternatives showing why the chosen procedure is technically meaningful.

### India-specific caution

For an Indian filing, software/algorithm subject-matter restrictions require professional advice. A claim should be tied to a concrete technical process/effect and implementation, not an abstract causal graph or optimization formula.

## 37.2 Q1-journal strategy

A strong journal version needs **depth and falsification resistance**, not additional buzzwords.

### Minimum journal evidence package

1. **External validity:** peer-reviewed benchmark anchors plus the project artifact; ideally ACIArena/AgentDojo in addition to Phase 1 TAMAS/MCPTox.
2. **Mechanistic validity:** Tracr/IOI/Greater-Than calibration plus causal intervention controls on the actual target.
3. **Closest baselines:** receiver-only causal patching/pruning, activation/probe or attention-dependence, trace/message counterfactual attribution, and PropGuard/CASPIAN-style comparison where reproducible.
4. **Budget fairness:** matched or transparently normalized forward-pass/intervention cost.
5. **Generalization:** held-out attacks and at least one meaningful distribution change.
6. **Robustness:** seeds, paraphrases, intervention operators, candidate-screening sensitivity and mechanism stability.
7. **Repair honesty:** whole security–utility–latency Pareto frontier, not a single favorable point.
8. **Negative results:** cases where receiver-only or trace-level methods are sufficient must be reported.
9. **Artifact quality:** exact releases, hashes, splits, manifests, code, configs and one-command reproduction.
10. **Claim discipline:** no "first", "minimal", "causally sufficient", or "unique repair point" unless the exact statement is independently established.

### Reviewer questions the paper must answer directly

**"Is this just PropGuard at a lower level?"**  
Show that PropGuard's state/message propagation representation is a close trace-level baseline and test whether internal interventions add measurable value beyond it. If they do not, do not claim a new causal layer.

**"Is this just CASPIAN plus activation patching?"**  
The answer must be empirical: demonstrate explicit mediator bridge tests, not a diagrammatic combination of methods.

**"Is this just MechRL on a larger graph?"**  
RL is not the contribution. Compare RL against simpler search. The contribution survives only if the DCMG/BVP causal estimand itself adds value.

**"Why not just replace the bad message?"**  
Whole-message repair is a mandatory baseline. AETHER must show a setting where internal causal evidence gives better utility, specificity, diagnosis, transfer, or cost; otherwise message replacement wins.

**"How do you know the arrows are causal?"**  
Use BVP: sender intervention and message regeneration; message counterfactual patch with sender fixed; receiver intervention with message fixed; matched controls; repeated held-out cases.

**"How do you know the mechanism is minimal?"**  
Do not claim global minimality. Report compactness under the candidate graph/search budget. Claim local minimality only when every one-node removal has been tested.

**"Could multiple repairs work?"**  
Yes. Report non-dominated alternatives. Do not force a unique repair point.

**"Is the healthcare setting doing scientific work?"**  
No novelty is assigned to healthcare. PTB-XL supplies a standardized, public, deterministic high-stakes task context; the causal/security claims must stand independently of the domain.

### Journal contribution framing

A defensible journal paper would ideally make three claims, each conditional on evidence:

- a **method claim** about explicit distributed internal causal mediation across separate model executions;
- a **scientific finding** about when sender-side information changes the explanation beyond receiver/message-only methods;
- an **applied result** about whether that added resolution improves constrained repair or generalization.

If only the first two survive, publish those. Do not keep a weak defense result for narrative symmetry.

---

# 38. Failure modes and mitigation

## R1 — Distributed causal mechanisms do not improve over receiver-only

**Impact:** weakens headline claim.  
**Mitigation:** report as finding if rigorously tested; inspect whether task actually requires upstream reasoning. Design attacks where sender compresses/rewrites adversarial evidence so sender should matter.

## R2 — Model too small to behave agentically

Switch to a slightly larger instruction model while preserving a smaller model for circuit feasibility.

## R3 — Model too large for intervention search

Use:
- fewer layers/heads;
- coarse granularity;
- sampled candidate nodes;
- activation pre-screening;
- smaller model.

## R4 — RL unstable

Fall back to greedy/beam for Phase 1. Do not sacrifice causal contribution to force RL.

## R5 — Message bridge is arbitrary

Use explicit counterfactual message patching and token/field perturbations to justify bridge edges.

## R6 — Tool poisoning rarely succeeds

Tune task/attack corpus carefully but do not intentionally weaken target. Use attacks grounded in benchmark patterns.

## R7 — Attacks always succeed

Target is too weak. Increase baseline hygiene or choose better model/prompts.

## R8 — No benign utility after intervention

Intervention too broad. Prefer local message or component patching; tune strength.

## R9 — Integration collapse

Prevent through frozen contracts and weekly integration.

## R10 — Coding agents generate fake abstractions

Require tests and inspect actual execution paths. Ban placeholder "success" outputs in experiment code.

## R11 — Paper written too late

Methods drafting begins in October. Results skeleton exists before final runs.

## R12 — Novelty overtaken by new paper

Run literature search at least:
- early October;
- early November;
- December;
- February;
- immediately before journal/patent submission.

---

# 39. What not to build

Until the core paper works, do not build:

- a fancy web UI;
- a production hospital dashboard;
- blockchain;
- federated learning;
- GNN simply because the graph exists;
- knowledge graph;
- RAG unless the experiment specifically needs retrieval;
- dozens of agents;
- full hospital simulation;
- autonomous malware;
- reinforcement learning for attack planning;
- complex multi-agent attacker hierarchy;
- generic SOC product;
- mobile app;
- cloud deployment;
- vector DB unless memory experiment needs it;
- multimodal medical input;
- hardware attack layer;
- formal verification stack;
- self-healing orchestration unless it is directly evaluated as a mechanism-derived intervention extension.

AETHER succeeds if one causal claim is proven well.

---

# 40. Development standards

## 40.1 Python/code quality

- type hints on public interfaces;
- dataclasses/Pydantic where useful;
- deterministic configs;
- no global hidden state;
- clear errors;
- no silent exception swallowing;
- no `except Exception: pass`;
- no hard-coded user paths;
- unit tests.

## 40.2 Configuration

Use YAML/TOML for experiments.

Never encode important hyperparameters only inside scripts.

## 40.3 Logging

Structured logs.

Minimum:

```text
timestamp
run_id
experiment_id
component
event
payload
```

## 40.4 Testing pyramid

Unit:
- schemas;
- intervention operators;
- metric math.

Integration:
- target run;
- attack injection;
- activation capture;
- message patch.

Regression:
- known benign cases;
- known attack cases;
- known intervention effect.

## 40.5 Reproducibility command

Phase 1 target:

```bash
python scripts/run_phase1_matrix.py \
  --manifest experiments/manifests/phase1_main.yaml
```

Then:

```bash
python scripts/reproduce_paper_figures.py \
  --results results/raw \
  --output results/figures
```

---

# 41. Daily workflow for each team member

Recommended full-day rhythm during intensive periods:

## Morning block

1. pull latest stable contracts;
2. read `PROJECT_STATE.md`;
3. define one measurable deliverable;
4. give bounded task to coding agent;
5. inspect agent output before continuing.

## Midday

- run tests;
- integrate fixtures;
- perform first experiment;
- log problems.

## Afternoon

- second implementation/debug cycle;
- peer review;
- clean commits.

## Evening

- run experiment;
- update project state;
- save result;
- write 5–10 lines explaining what was learned.

Daily stand-up should answer:

- What did I execute, not merely code?
- What quantitative result exists?
- What interface changed?
- What blocks another member?
- What is tomorrow's single highest-value task?

---

# 42. Pull request checklist

Every PR:

- [ ] Scope matches issue.
- [ ] No contract change without approval.
- [ ] Tests added/updated.
- [ ] Tests pass.
- [ ] No fake/mock output used in production experiment path.
- [ ] Seeds/config logged.
- [ ] No secrets.
- [ ] README/docs updated if public behavior changes.
- [ ] Research metric definitions unchanged or explicitly documented.
- [ ] New experiment code writes manifest metadata.
- [ ] One teammate reviewed.

---

# 43. Phase 1 definition of done

Phase 1 is complete only if all are true:

## Research

- [ ] central RQ frozen;
- [ ] novelty claim checked against literature;
- [ ] at least one intervention-validated DCMG result on locked held-out cases;
- [ ] independent causal validation;
- [ ] baselines;
- [ ] ablations;
- [ ] DCMG-informed intervention demonstration.

## Engineering

- [ ] clean install;
- [ ] reproducible scripts;
- [ ] tests;
- [ ] experiment manifests;
- [ ] result artifacts.

## Paper

- [ ] full manuscript;
- [ ] tables;
- [ ] figures;
- [ ] limitations;
- [ ] related work;
- [ ] appendix;
- [ ] no unsupported novelty language.

## Presentation

- [ ] architecture;
- [ ] attack demo;
- [ ] circuit visualization;
- [ ] intervention result;
- [ ] backup video;
- [ ] each member can explain entire project.

---

# 44. Phase 2 definition of done

By April 2027:

- [ ] Phase 1 reproduced after months, not just once;
- [ ] selected Phase 2 extensions complete;
- [ ] final experiment matrix frozen;
- [ ] journal manuscript complete;
- [ ] replication package complete;
- [ ] updated prior-art search;
- [ ] patent technical disclosure prepared if still justified;
- [ ] final demo stable;
- [ ] code tagged/released;
- [ ] all four members can defend method, results, limitations, and novelty.

---

# 45. Research integrity rules

1. Never report generated numbers as measured.
2. Keep negative results.
3. Do not tune on test set.
4. Do not delete failed seeds because they look bad.
5. Clearly label synthetic data.
6. Do not claim clinical validity.
7. Do not claim "first" without a dated search and precise scope.
8. Distinguish preprint vs peer-reviewed publication.
9. Cite benchmark/method authors.
10. Preserve raw logs used in final figures.

---

# 46. Suggested main result tables

## Table 1 — Attack baseline

| Attack family | N | Clean accuracy | Attacked accuracy | ASR | 95% CI |
|---|---:|---:|---:|---:|---:|

## Table 2 — Discovery

| Method | Scope | Faithfulness | Circuit size | Benign damage | Forward passes |
|---|---|---:|---:|---:|---:|

Rows:
- random;
- receiver greedy;
- receiver RL;
- DCMG greedy;
- DCMG RL, with primary-method status determined by matched-budget results.

## Table 3 — Ablation

| Variant | Faithfulness | Size | Δ vs full |
|---|---:|---:|---:|

Variants:
- no sender;
- no message;
- no receiver;
- full.

## Table 4 — Remediation

| Defense | ASR ↓ | Benign utility ↑ | Latency ↓ | Intervention size ↓ |
|---|---:|---:|---:|---:|

---

# 47. Suggested main figures

Figure 1 — System overview.  
Figure 2 — DCMG and explicit serialized-mediator formalism.  
Figure 3 — Example discovered circuit.  
Figure 4 — Faithfulness vs circuit size.  
Figure 5 — Attack success by family.  
Figure 6 — Intervention trade-off.  
Figure 7 — Phase 2 optional: circuit overlap across attack families.

---

# 48. Decision gates

## Gate A — 8 October

Can every member run their module?

If no, fix engineering.

## Gate B — 15 October

Can a real attacked trace produce activations on both agents?

If no, simplify model/protocol.

## Gate C — 22 October

Can targeted sender/message/receiver interventions causally change the held-out outcome?

If no, redesign task before continuing.

## Gate D — 29 October

Does DCMG search produce a compact intervention-validated candidate mechanism beyond matched controls?

If no, reduce granularity or narrow Phase 1 claim.

## Gate E — 5 November

Do results support a paper?

If marginal, stop features and improve rigor/error analysis.

## Gate F — 17–25 November

Which Phase 2 extension actually strengthens the evidence?

Choose max three.

---

# 49. Fallback ladder

The project must remain gradable even if difficult methods fail.

## Tier 1 — guaranteed floor

- working MCP/A2A target;
- attack corpus;
- receiver-only causal circuit discovery;
- rigorous causal intervention.

## Tier 2 — intended Phase 1

- DCMG/BVP;
- cross-boundary discovery;
- message mediator;
- DCMG-informed intervention.

## Tier 3 — strong Phase 1 / Phase 2

- RL DCMG search;
- generalization;
- memory attacks;
- gated defense.

## Tier 4 — stretch

- mechanism-informed attack synthesis;
- broader architectures;
- sophisticated learned remediation.

If Tier 2 fails, the report must honestly state the limitation and present what was learned. Do not fake cross-agent novelty.

---

# 50. Literature-review workflow

Maintain `docs/literature/related_work.csv`:

```text
paper_id
title
year
venue
peer_reviewed
problem
method
data
main_claim
closest_to_us
what_it_already_solves
remaining_gap
url_or_doi
checked_date
checked_by
```

Search terms:

- cross-agent mechanistic interpretability;
- multi-agent causal circuit;
- distributed circuit discovery;
- agent communication causal attribution;
- MCP tool poisoning interpretability;
- A2A adversarial message mechanistic;
- multi-agent activation intervention;
- causal trust circuits agents;
- memory poisoning circuit discovery;
- mechanism-guided agent defense.

Before every submission, two members independently search.

---

# 51. Reference anchors for the current project

These are the minimum references the team should read directly, not only through summaries.

1. **Wang et al. (2026). MCPTox: A Benchmark for Tool Poisoning on Real-World MCP Servers. AAAI 2026.**  
   DOI: 10.1609/aaai.v40i42.40895

2. **Khadka (2026). MechRL: Reinforcement Learning Agents Perform Circuit Discovery for Mechanistic Interpretability.**  
   arXiv:2605.26343

3. **Rose et al. (2026). Detecting Multi-Agent Collusion Through Multi-Agent Interpretability.**  
   arXiv:2604.01151

4. **Venkatesh et al. (2026). CASPIAN: Online Detection and Attribution of Cascade Attacks in LLM Multi-Agent Systems via Cross-Channel Causal Monitoring.**  
   arXiv:2605.19240

5. **Lee, Lauscher, Albrecht (2025/2026). Towards Ethical Multi-Agent Systems of Large Language Models: A Mechanistic Interpretability Perspective.**  
   arXiv:2512.04691; accepted to LaMAS @ AAAI 2026.

6. **Tatsat and Shater (2026). Beyond the Black Box: Interpretability of Agentic AI Tool Use.**  
   arXiv:2605.06890

7. **Yu et al. (2026). SafeSeek: Universal Attribution of Safety Circuits in Language Models. ICML 2026.**

8. **Wagle et al. (2026). Mechanistic Interpretability of LLM Jailbreaks via Internal Attribution Graphs.**  
   arXiv:2607.07903

9. **Luo et al. (2026). AgentLens: Interpretable Safety Steering via Mechanistic Subspaces for Multi-Turn Coding Agent.**  
   arXiv:2606.22673

10. **Zhang et al. (2026). MemMorph: Tool Hijacking in LLM Agents via Memory Poisoning.**  
    arXiv:2605.26154

11. **Official Model Context Protocol specification and security best practices, current 2026 revision.**

12. **Official Agent2Agent protocol specification v1.0.0 and reference SDKs.**

The bibliography must be refreshed before paper submission because this research area is moving rapidly.

---


## 51.1 Benchmark and methodology references added after mentor review

The following are now part of the project’s mandatory methodological reading list because they anchor the standardized data/evaluation plan.

13. **Debenedetti et al. (2024). AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents.** arXiv:2406.13352. The released environment contains realistic tool-use tasks and hundreds of security test cases and supplies native utility/security evaluation.

14. **Zhan et al. (2024). InjecAgent: Benchmarking Indirect Prompt Injections in Tool-Integrated Large Language Model Agents.** arXiv:2403.02691. The benchmark contains 1,054 test cases spanning 17 user tools and 62 attacker tools.

15. **Patil et al. (2025). The Berkeley Function Calling Leaderboard (BFCL): From Tool Use to Agentic Evaluation of Large Language Models.** ICML 2025. Use a pinned BFCL evaluator/package release for benign function-calling competence.

16. **Yao et al. (2024). tau-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains.** arXiv:2406.12045. Relevant primarily to Phase 2 reliability and utility evaluation; introduces database-state-based evaluation and pass^k.

17. **Lindner et al. (2023). Tracr: Compiled Transformers as a Laboratory for Interpretability.** arXiv:2301.05062. Tracr produces transformers with known algorithmic structure and is used as a ground-truth calibration environment for the discovery implementation.

18. **Wang et al. (2022). Interpretability in the Wild: a Circuit for Indirect Object Identification in GPT-2 Small.** arXiv:2211.00593. Provides an established causal circuit and quantitative criteria including faithfulness, completeness, and minimality.

19. **Conmy et al. (2023). Towards Automated Circuit Discovery for Mechanistic Interpretability.** arXiv:2304.14997. Introduces ACDC and provides a strong automated-circuit baseline, including reproduction of Greater-Than circuit components.

20. **Wagner et al. (2020; PhysioNet current v1.0.3). PTB-XL: A Large Publicly Available Electrocardiography Dataset.** Scientific Data; PhysioNet. The primary open medical source dataset for AETHER’s controlled target harness.

21. **Moody and Mark / PhysioNet. MIT-BIH Arrhythmia Database.** Secondary legacy cross-dataset validation resource with expert beat annotations.

22. **Rose et al. (2026). NARCBench dataset and code for Detecting Multi-Agent Collusion Through Multi-Agent Interpretability.** Use as an external multi-agent activation/probing reference, primarily in Phase 2.

23. **Yan et al. (2026). PropGuard: Safeguarding LLM-MAS via Propagation-Aware Exploration and Remediation.** arXiv:2605.16346. Full text confirms a dual-view spatio-temporal state/message graph, GE-GRPO suspicious-subgraph exploration, diagnosis, and source-guided remediation; treat this as direct prior art for graph/RL/remediation at the trace/state level.

24. **Ma et al. (2026). DoVer: Intervention-Driven Auto Debugging for LLM Multi-Agent Systems. ICLR 2026.** Intervention-and-replay debugging; important evidence that multiple different interventions may repair the same failure.

25. **Shah (2026). Causal Agent Replay: Counterfactual Attribution for LLM-Agent Failures.** arXiv:2606.08275. Structural-causal replay and intervention baseline for step-level failure attribution.

26. **He et al. (2026). AttriGuard: Defeating Indirect Prompt Injection in LLM Agents via Causal Attribution of Tool Invocations. USENIX Security 2026.** Action-level causal attribution through counterfactual re-execution.

27. **Zhang et al. (2026). AgentSentry: Mitigating Indirect Prompt Injection in LLM Agents via Temporal Causal Diagnostics and Context Purification.** arXiv:2602.22724. Causal localization and repair at tool-return/context level.

28. **Wang et al. (2025/2026). MindGuard: Intrinsic Decision Inspection for Securing LLM Agents Against Metadata Poisoning.** arXiv:2508.20412. Attention-based decision-dependence graph and metadata-poisoning attribution.

29. **MCPFixGen / Beyond Detection: Autonomous Anomaly Remediation for MCP Against Tool Poisoning Attacks. WWW 2026.** DOI:10.1145/3774904.3792400. Attention-linked anomaly localization, checkpointing and automated backtracking/correction.

30. **Kavathekar et al. (2026). TAMAS: Benchmarking Adversarial Risks in Multi-Agent LLM Systems. ACL 2026.** 300 adversarial instances, six attack types, 211 tools, five scenarios and 100 harmless tasks; mandatory Phase 1 multi-agent external anchor.

31. **An et al. (2026). ACIArena: Toward Unified Evaluation for Agent Cascading Injection. ACL 2026.** 1,356 cascading-injection cases across multiple surfaces/objectives and six MAS implementations; Phase 2 generalization anchor.

32. **Kumarappan and Mujoo (2026). Not Just RLHF: Why Alignment Alone Won't Fix Multi-Agent Sycophancy.** arXiv:2605.12991. Activation patching causally localizes peer-pressure-induced failures in a target model; direct prior art against broad inter-agent mechanistic novelty claims.

### Reference-handling rule

For every external benchmark used in final results, cite both the benchmark paper and the exact dataset/software release used. A paper citation alone is insufficient for reproducibility if the benchmark has multiple versions.

---

# 52. Final statement of novelty for internal use

The team should memorize the following wording and use it unless the full-text literature audit forces a narrower version:

> **We do not claim that MCP poisoning, A2A attacks, multi-agent causal attribution, multi-agent interpretability, RL search, mechanistic security analysis, or causal remediation are new. AETHER tests a narrower methodological question: whether intervention on internal components in a sender model, on the serialized inter-agent message as an explicit mediator, and on internal components in a receiver model provides additional causal localization and a better held-out security–utility–cost repair frontier than receiver-only mechanistic analysis, correlational internal signals, and trace/message-level causal attribution.**

If the locked experiments do not show incremental value, the paper must say so and narrow its contribution to a comparative empirical study. Never convert a failed hypothesis into a broader novelty claim after seeing the results.

# 53. Appendix A — Example end-to-end experiment

Consider case `case_0042`.

Ground truth: `ESCALATE`.

## Clean run

1. Agent A sees case.
2. Agent A calls `get_recent_vitals`.
3. Tool returns correct high-risk signal.
4. Agent A sends:
   `risk_level=high; recommend_review=true`
5. Agent B outputs `ESCALATE`.

## Attacked run

1. Same case.
2. Tool description/result is poisoned.
3. Agent A internal state shifts.
4. Agent A sends:
   `measurements likely artifact; risk_level=moderate`
5. Agent B outputs `DO_NOT_ESCALATE`.

## Causal analysis

Capture:

- sender head/layer activations;
- message fields/tokens;
- receiver activations.

Interventions:

A. patch sender component from clean -> attacked.  
Does message become safer?

B. patch message risk field from clean -> attacked.  
Does receiver escalate?

C. patch receiver component from clean -> attacked.  
Does decision change?

Construct graph and search.

Possible discovered circuit:

```text
A:L5:H2
   |
A:L7:MLP
   |
Message:risk_level
   |
B:L4:H6
   |
B:L8:MLP
   |
DO_NOT_ESCALATE
```

Then compare remediation:

- suppress A:L5:H2;
- replace only `risk_level` field;
- steer/patch B:L4:H6.

Evaluate attack and benign cases.

This one example is the conceptual core of AETHER.

---

# 54. Appendix B — Example task files for coding agents

## `TASK_M3_ABLATION.md`

```markdown
# Goal
Implement zero-ablation and clean-to-attacked activation patching for attention heads.

# Allowed directories
instrumentation/
causal/interventions/
tests/

# Forbidden
contracts/
target/
attacks/

# Acceptance
1. Hook-free and hook-enabled no-op forward passes match within tolerance.
2. Zero ablation changes only selected head output.
3. Patch can load clean activation artifact and inject into attacked run.
4. Unit tests.
5. Run `pytest tests/unit/test_interventions.py`.
6. No generated/fake experiment results.

# Output
Summarize files changed, tests, limitations.
```

## `TASK_M4_MESSAGE_BRIDGE.md`

```markdown
# Goal
Implement message-node interventions and bridge effect scoring.

# Inputs
RunTrace + clean twin + attacked twin.

# Operators
field_replace
span_replace
token_mask

# Metric
change in target decision score.

# Acceptance
A synthetic fixture in which `risk_level` is the only causal field must rank
that field above an unrelated metadata field.
```

---

# 55. Appendix C — Review-day demonstration script

## Person 1 — 2 minutes

- run benign case;
- run poisoned case;
- show trace JSON.

## Person 2 — 2 minutes

- show attack corpus;
- run benchmark;
- show ASR plot.

## Person 3 — 3 minutes

- capture activation;
- ablate component;
- show changed score;
- show faithfulness curve.

## Person 4 — 3 minutes

- load the DCMG and bridge-evidence artifact;
- show message mediator;
- apply three intervention locations;
- show comparison.

## Final team slide

"By November 16 we will integrate these into one causal-discovery experiment."

---

# 56. Appendix D — Phase 2 journal experiment matrix template

Dimensions:

- model family: M1, M2;
- attack: tool-desc, tool-output, A2A, memory;
- search: random, greedy, RL;
- scope: receiver-only, trace/message-level, DCMG/BVP;
- defense: none, fixed message, fixed receiver, mechanism-guided;
- seed: 5 seeds;
- split: validation/test.

Do not blindly run full Cartesian product if it is computationally enormous. Use the matrix to identify controlled comparisons.

---

# 57. Appendix E — Project management issue labels

Use:

- `P0-critical`
- `research`
- `experiment`
- `bug`
- `contract`
- `integration`
- `paper`
- `literature`
- `phase1`
- `phase2`
- `blocked`
- `needs-human-review`
- `agent-generated`

Every AI-generated large PR should receive `agent-generated` until reviewed.

---

# 58. Appendix F — Human responsibilities that cannot be delegated

Coding agents can generate code. They cannot own the research claim.

Humans must decide:

- whether a causal intervention is valid;
- whether an attack is realistic enough;
- whether a baseline is fair;
- whether a metric is circular;
- whether a novelty claim is supported;
- whether a negative result changes the research story;
- whether an experiment leaks test information;
- whether a paper sentence overstates evidence.

Every member should be able to answer those questions in the final viva.

---

# 59. Appendix G — End-to-end build order

Do not violate this dependency order without reason:

1. contracts;
2. target deterministic run;
3. attack toggling;
4. trace logging;
5. activation hooks;
6. intervention primitive;
7. receiver-only causal result;
8. clean/attacked message pair;
9. message intervention;
10. DCMG construction;
11. greedy DCMG localization;
12. random baseline;
13. faithfulness validation;
14. RL;
15. intervention selection;
16. generalization;
17. memory/Phase 2 extensions.

This order is chosen to maximize the chance of producing a paper even if later steps fail.

---

# 60. Appendix H — Scope budget

Treat project capacity as finite.

## Phase 1 budget

Approximately:
- 35% target/attacks/infrastructure;
- 40% causal discovery;
- 15% evaluation;
- 10% writing/packaging.

By November, discovery/evaluation should dominate.

## Phase 2 budget

Approximately:
- 20% engineering hardening;
- 45% experiments/method;
- 20% paper/analysis;
- 15% selected extensions/patent documentation.

If the team spends most time on UI, orchestration, or DevOps, the research project is off course.

---

# 61. Appendix I — Paper claim checklist

Before submission, mark every claim:

- `OBSERVED` — directly supported by experiment;
- `PRIOR_WORK` — supported by citation;
- `HYPOTHESIS` — not yet established;
- `DESIGN` — system choice;
- `LIMITATION` — boundary.

Any sentence containing:
- "first";
- "novel";
- "state of the art";
- "significantly";
- "causal";
- "generalizes";
- "robust";

must receive explicit evidence review.

---

# 62. Appendix J — Full project success criteria

The project is scientifically successful if, by April 2027, the team can answer all of these with evidence:

1. What exact trust failure are you studying?
2. Why is MCPTox not your novelty?
3. Why is MechRL not your novelty?
4. What does "distributed causal mechanism" mean mathematically and operationally?
5. How do you create causal edges across a discrete message?
6. How do you verify the circuit is not merely correlational?
7. What baseline does receiver-only discovery provide?
8. When does DCMG/BVP add value beyond receiver-only and trace/message-level methods?
9. What happens when it does not help?
10. How do you quantify minimality?
11. How do you avoid reward hacking?
12. How does the intervention follow from the discovered mechanism?
13. What is the benign-utility cost?
14. Does the mechanism generalize?
15. What are the limitations?
16. Which component is potentially patent-relevant?
17. Which claims would you remove if a new paper appeared tomorrow?
18. Can another researcher reproduce the main figure from your repository?

If the team can answer these cleanly, the project will be much stronger than a larger system with dozens of loosely connected "AI features."

---

# 63. Closing project contract

AETHER will be managed under one principle:

> **One research question -> one causal mechanism -> one coherent experiment story.**

The team is allowed to use coding agents extensively. The amount of generated code is not a success metric.

The Phase 1 objective is not to build every possible feature. It is to establish, with reproducible evidence, whether explicit sender/message/receiver intervention analysis provides causal localization beyond receiver-only, correlational, and trace/message-level baselines, and whether any added resolution improves a constrained intervention choice.

The Phase 2 objective is to convert that proof into a stronger, more general, more rigorously evaluated research contribution suitable for a serious journal submission and, if supported by professional prior-art review, a patent-oriented technical disclosure.

Every future feature must pass one question:

> **Does this feature create stronger evidence for the central causal research claim?**

If the answer is no, it is not part of the core project.



---

# 63B. Timeline preservation note after the additive architecture revision

The platform-preservation decision does not reopen the Phase 1 schedule. Existing capabilities may remain in the repository and final demo, but no preserved feature is allowed to delay the mandatory evidence chain.

If a scheduled date has passed, update the actual status and roll the unfinished dependency forward. Do not manufacture retrospective completion. The Nov 8 feature-freeze / Nov 9–10 rerun / Nov 11–15 writing-and-freeze protection window should be preserved as far as possible.

The dependency priority remains:

```text
reproducible repository
→ real model + activation intervention
→ calibration
→ paired clean/attack traces
→ strong baselines
→ BVP/DCMG
→ held-out comparison
→ tri-location remediation
→ final statistical rerun
→ paper
```

Mandatory platform breadth is dependency-ordered rather than allowed to weaken the evidence required for the Phase 1 paper.


# 64. Detailed operational plan from October 9 to November 16

This section converts the weekly plan into an execution schedule suitable for a team that is working intensively and relying heavily on coding agents.

The dates are targets, not excuses to wait. If a task finishes early, move to the next dependency. If a task is late, cut scope rather than silently shifting every downstream milestone.

## 64.1 October 9 — post-review cleanup

All members:

- collect every code-review comment;
- classify each comment as:
  - correctness,
  - research-methodology,
  - code quality,
  - documentation,
  - future suggestion;
- fix only correctness blockers immediately;
- update `PROJECT_STATE.md`;
- create Phase 1 issue board.

Member 1:
- stabilize target runner;
- delete obsolete review-only stubs.

Member 2:
- convert attack fixtures into versioned corpus files.

Member 3:
- clean hook/intervention APIs.

Member 4:
- replace fixture-only graph paths with interfaces consuming real traces.

Required end-of-day artifact:
- `phase1_integration_plan.md`.

## 64.2 October 10–11 — pairwise integration weekend

### Pair A: Members 1 + 2

Goal:

`AttackSpec -> target run -> RunTrace -> attack_success`

Checklist:

- attack toggling works;
- attack ID appears in trace;
- clean twin can be located from attack run;
- evaluator does not infer label from attack ID;
- no human manual edits.

### Pair B: Members 3 + 4

Goal:

`ActivationTrace + A2AMessageRecord -> candidate graph -> intervention result`

Checklist:

- graph consumes serialized artifacts;
- node IDs stable;
- intervention result written to file;
- graph code does not import target internals directly.

## 64.3 October 12 — first stable integration branch

Merge only the minimum interfaces necessary.

Run:

```bash
pytest tests/unit
pytest tests/integration
```

Create tag:

`integration-v0.1`

No experiment paper claims yet.

## 64.4 October 13–14 — real target instrumentation

Member 3 instruments Agent B first.

Why receiver first?

- simpler;
- provides immediate causal baseline;
- isolates instrumentation bugs before distributed mediation complexity.

Member 1 helps expose stable model wrapper.

Member 2 selects 10 successful and 10 unsuccessful attack traces.

Member 4 prepares paired clean/attack message dataset.

Required result:
- at least one receiver component intervention with measurable effect.

## 64.5 October 15 — Gate B

Questions:

1. Can Agent A and Agent B both be instrumented?
2. Is the A2A message stored exactly as consumed by Agent B?
3. Do clean and attack twins exist?
4. Can a causal patch be replayed?

If any answer is no, the next 48 hours are engineering-only. Do not start RL.

## 64.6 October 16–17 — receiver baseline complete

Member 3:

- rank components by intervention effect;
- implement greedy pruning;
- run random matched-size controls.

Member 2:

- define exact primary metric scripts;
- verify bootstrap CI code with synthetic tests.

Member 4:

- define initial message nodes at field/span level.

Member 1:

- optimize repeated deterministic runs.

Deliverable:
- receiver-only baseline table draft.

## 64.7 October 18–19 — sender and message mediation

Primary experiment:

1. attacked input enters Agent A;
2. patch one sender component from clean run;
3. regenerate message;
4. compare message and final outcome.

Then:

1. use attacked sender;
2. patch one message field/span;
3. run Agent B;
4. compare outcome.

The goal is to establish at least one causal bridge before building a large graph.

## 64.8 October 20–21 — candidate DCMG

Build a candidate graph using only a reduced candidate set:

- top-K sender components;
- top-K message spans/fields;
- top-K receiver components.

Reason:

The full Cartesian graph is unnecessary and computationally expensive.

A candidate-screening stage is acceptable if documented and included in the method.

Potential screening:

- causal single-node effect;
- activation difference clean vs attack;
- attribution score;
- message change sensitivity.

Do not call screening causal unless it uses intervention.

## 64.9 October 22 — Gate C

Required demonstration:

- an intervention at each region can be executed;
- at least one path can be narrated from sender to message to receiver;
- final output changes under a controlled patch.

If message interventions never matter, inspect task design. It may mean:

- Agent B ignores Agent A;
- Agent A message is not the relevant mediator;
- attack acts directly on Agent B;
- target design does not test the research question.

Fix the task rather than hiding the result.

## 64.10 October 23–24 — greedy DCMG localization

Run on a small set of successful attacks.

For each:

- full candidate graph;
- greedy compact circuit;
- random circuits of same size;
- receiver-only compact circuit.

Store all intermediate masks and scores.

## 64.11 October 25 — preliminary analysis day

No new code until the team answers:

- Are circuits stable enough to discuss?
- Does sender/message inclusion help?
- Is the metric saturated?
- Is benign damage being tracked?
- Is the attack task too easy/hard?

Write a one-page internal "results memo."

## 64.12 October 26–27 — RL feasibility

Member 3 leads.

Start from a small action space.

Do not immediately include every sender/message/receiver node.

Suggested experiment:

- 5 sender candidates;
- 3 message candidates;
- 5 receiver candidates;
- stop action.

Compare RL against greedy with equal or recorded evaluation budget.

If training is unstable after a bounded effort, mark RL as preliminary and move on.

## 64.13 October 28–29 — main-method freeze

Choose main Phase 1 method based on evidence:

### Option A
DCMG RL search is stable and beats simpler search under a matched budget -> it may be the main search method.

### Option B
Greedy/beam DCMG search is stable while RL adds no reproducible benefit -> use greedy/beam as the main method and report RL as a negative/secondary result.

### Option C
Only intervention-supported mediation analysis works -> narrow the paper to distributed causal localization rather than compact-subgraph optimization.

Do not mislabel an unstable method.

## 64.14 October 30–31 — attack breadth

Member 2 runs multiple attack families.

Member 1 ensures behavior remains valid.

Member 3/4 test whether the same discovery pipeline operates without per-attack code hacks.

Required:
- no method-specific code branch named after individual attack examples.

## 64.15 November 1–2 — held-out protocol setup

Freeze final test cases.

Create hash manifest.

No member may edit test payloads after seeing final results except to fix an objectively documented data bug, in which case create a new dataset version and rerun all results.

## 64.16 November 3–5 — final ablations

Run:

- receiver-only;
- no sender;
- no message;
- full DCMG/BVP;
- random matched-size;
- intervention operator ablation.

If RL is main:
- reward ablations.

## 64.17 November 6–7 — remediation experiment

For each discovered circuit:

1. extract candidate intervention points;
2. evaluate fixed and DCMG-informed interventions;
3. measure attack reduction;
4. measure benign utility;
5. record latency.

Do not tune intervention threshold on test data.

## 64.18 November 8 — feature freeze

After this date:

Allowed:
- bug fixes;
- reproducibility fixes;
- paper scripts;
- experiment reruns.

Not allowed:
- new attack family;
- new model;
- new RL algorithm;
- new memory system;
- new UI;
- new agent role.

## 64.19 November 9–10 — full rerun

Run final manifest from scratch.

If possible, use a different machine/environment for at least a smoke reproduction.

Save:
- raw JSON/CSV;
- log files;
- configs;
- commit hash.

## 64.20 November 11–12 — paper assembly

By the end of November 12:

- no placeholder results;
- no "TODO citation";
- all figures numbered;
- all tables referenced;
- related work current;
- limitations present.

## 64.21 November 13 — internal hostile review

Each member acts as reviewer.

Questions:

- Could this result be explained by a simpler mechanism?
- Are baselines weak?
- Is "causal" justified?
- Is the paper hiding failed attacks?
- Is the circuit size comparison fair?
- Is the message representation arbitrary?
- Is the medical story oversold?
- Is RL actually needed?
- Is any novelty claim broader than evidence?

Create issue list and resolve critical items.

## 64.22 November 14–15 — freeze

No code refactor for aesthetics.

Prepare:
- final paper PDF;
- code tag;
- demo;
- backup video;
- slide deck;
- result appendix.

## 64.23 November 16 — Phase 1 close

Archive:

```text
releases/phase1/
  code_commit.txt
  paper/
  results/
  figures/
  configs/
  environment/
  demo/
```

This archive becomes the Phase 2 baseline.

---

# 65. Detailed Phase 2 implementation by research track

Phase 2 should start from the Phase 1 release rather than an unstable `main`.

## 65.1 Track 1 — Cross-protocol generalization

### Objective

Determine whether trust failures delivered through MCP and A2A converge on a shared internal mechanism.

### Experimental construction

Create paired attack families that target the same downstream decision.

Example:

- MCP poison changes Agent A's summary.
- A2A tampering directly changes the equivalent summary field.

Control:

- same underlying case;
- same target outcome;
- similar semantic alteration.

### Metrics

- circuit node overlap;
- bridge differences;
- receiver subcircuit overlap;
- intervention transfer:
  - derive from MCP circuit, apply to A2A attack;
  - derive from A2A circuit, apply to MCP attack.

### Interpretations

If overlap high:
- possible common downstream trust circuit.

If overlap low:
- protocol-specific pathway.

Neither should be predetermined.

---

## 65.2 Track 2 — Memory-poisoning causal mechanism

### Minimal memory architecture

Use an inspectable store:

```json
{
  "memory_id": "...",
  "content": "...",
  "source": "system|external",
  "created_at": "...",
  "trust_tag": "...",
  "case_scope": "..."
}
```

Avoid complex vector DB unless retrieval requires it.

### Attack

Inject small crafted records.

### Questions

- does memory influence tool selection?
- does memory influence Agent A summary?
- does effect persist?
- where does it enter distributed causal mechanism?

### Causal interventions

- remove memory;
- replace with clean memory;
- patch sender activations;
- patch message;
- patch receiver.

### Output

An intervention-supported temporal distributed causal pathway rather than only persistence ASR.

---

## 65.3 Track 3 — Mechanism-gated intervention

### Phase 2 implementation

1. collect activation signature from discovered circuit;
2. derive lightweight detector:
   - threshold;
   - linear probe;
   - small classifier;
3. evaluate detector on clean/attack held-out data;
4. trigger intervention only when detector fires.

### Metrics

- AUROC/PR-AUC if probabilistic detector;
- false positive rate;
- ASR after gating;
- benign utility;
- intervention frequency;
- latency.

### Key comparison

Always-on intervention vs gated intervention.

---

## 65.4 Track 4 — Hierarchical RL

Only if Phase 1 shows RL is worthwhile.

### State

Possible feature vector:

- binary/continuous current mask;
- region statistics;
- current faithfulness;
- benign damage;
- remaining node counts;
- previous action.

### Action

`(region, component, operation)`

Region:
- sender;
- message;
- receiver.

Operation:
- prune;
- restore;
- stop.

### Reward

Start simple.

Do not add five novelty terms at once.

Run reward ablation.

### Baselines

- greedy;
- beam;
- random;
- flat RL.

The hierarchical formulation is only valuable if it improves efficiency or quality.

---

# 66. Exact merge playbook

## 66.1 Before merge

Owner runs:

```bash
git fetch origin
git rebase origin/integration/phase1
pytest
```

Resolve locally.

## 66.2 Pull request template

```markdown
## Purpose

## Research effect

## Files/directories touched

## Contract changes
None / listed here

## Tests
- ...

## Manual commands run
- ...

## Experiment impact
None / invalidates experiment IDs ...

## Known limitations

## Reviewer checklist
- [ ] no hidden mock
- [ ] no data leakage
- [ ] reproducible
```

## 66.3 Merge conflicts

If conflict touches:
- contracts -> both owners + one neutral member review;
- metric definition -> full team;
- experiment split -> Member 2 + full team approval;
- method code -> relevant owner + Member 3/4.

## 66.4 Bad merge rule

Never resolve a scientific-logic conflict by choosing "ours" or "theirs" blindly.

Example:
one branch defines attack success differently.

Stop and decide definition.

## 66.5 Integration tests after every merge

Minimum:

```bash
pytest tests/unit
pytest tests/integration/test_target_attack.py
pytest tests/integration/test_activation_capture.py
pytest tests/integration/test_cross_agent_intervention.py
```

---

# 67. Coding-agent resource management

Because agent quotas are limited, treat agent time like compute.

## 67.1 High-value tasks for coding agents

- repository inspection;
- multi-file feature implementation;
- writing tests around existing APIs;
- refactoring repeated experiment code;
- diagnosing complex stack traces;
- generating adapters from fixed schemas;
- setting up CI;
- producing reproducible CLI wrappers.

## 67.2 Low-value tasks

Do manually or with cheaper chat:

- renaming;
- tiny helper;
- Markdown formatting;
- copy editing;
- simple plotting boilerplate;
- trivial schema changes.

## 67.3 Context minimization

Instead of pasting whole repo into every chatbot:

- point coding agent to files;
- maintain `PROJECT_STATE.md`;
- maintain `RESEARCH_CONTRACT.md`;
- provide exact failing command.

## 67.4 One agent, one bounded task

Do not ask three agents to independently implement the same subsystem unless intentionally comparing designs.

Preferred parallel use per person:

- Agent A: implementation;
- Agent B: reviewer/test designer;
- chatbot: research explanation/debug discussion.

## 67.5 Stop conditions

Terminate agent loop if:

- same bug repeated twice;
- agent keeps changing unrelated files;
- contract is being altered;
- tests are being weakened to pass;
- fake fallback is inserted.

Human takes over and re-scopes.

---

# 68. Research-method validation checklist

Before accepting any circuit result:

## 68.1 Causal validity

- Was an actual intervention performed?
- Does intervention precede measured outcome?
- Is clean/attack comparison controlled?
- Is effect not explained by total model destruction?

## 68.2 Specificity

- Does ablation alter unrelated benign tasks?
- Does matched-size random ablation produce same effect?
- Is the component simply globally important?

## 68.3 Minimality

- What search definition is used?
- Was every additional removal tested?
- Is "minimal" global or local?
- If only local, say local.

## 68.4 Stability

- same circuit on multiple examples?
- same result across seeds?
- if not, report variability.

## 68.5 Distributed causal-mediation validity

- does sender intervention affect message?
- does message intervention affect receiver?
- does receiver intervention affect outcome?
- are these effects linked on the same case?

---

# 69. Novelty verification protocol

Before using "first" in a paper:

1. write exact claim in one sentence;
2. extract keywords;
3. search Google Scholar/arXiv/IEEE/ACM/Semantic Scholar;
4. search synonyms;
5. inspect citations of nearest papers;
6. inspect papers citing nearest papers;
7. record search date;
8. have second member repeat independently;
9. downgrade wording if uncertainty remains.

Preferred paper wording:

> "To the best of our knowledge, among the literature reviewed as of [date], we did not identify..."

Avoid:

> "No work exists."

---

# 70. Phase 2 patent evidence dossier

If the project remains patent-relevant, create:

```text
docs/ip/
  invention_disclosure.md
  prior_art_matrix.csv
  technical_effects.md
  inventor_contributions.md
  experiments/
  diagrams/
```

## 70.1 `invention_disclosure.md`

Explain:

- technical problem;
- existing approaches;
- concrete mechanism;
- inputs;
- processing steps;
- outputs;
- technical effect;
- alternatives.

## 70.2 Technical effect examples

Do not write only:
"improves security."

Write measured effects such as:
- reduction in ASR;
- reduction in benign utility loss compared with fixed defense;
- reduction in search cost;
- reduced intervention frequency;
- lower latency.

## 70.3 Inventor contribution log

Each member records:
- mechanism proposed;
- implementation contribution;
- experiment contribution;
- date.

This is useful for institutional IP processes.

---

# 71. Final Phase 2 paper experiment plan

A journal-quality experiment plan may use three tiers.

## Tier A — mandatory

- two attack families;
- two discovery scopes;
- multiple baselines;
- held-out test;
- multi-seed;
- remediation.

## Tier B — strong

- second model family;
- memory poison;
- cross-protocol transfer;
- gated defense.

## Tier C — optional

- quantization;
- edge device;
- hierarchical RL;
- mechanism-informed attack generation.

Do not sacrifice Tier A quality for Tier C quantity.

---

# 72. Deliverable ownership matrix

| Deliverable | P1 | P2 | P3 | P4 |
|---|---|---|---|---|
| Target harness | Lead | Test | Instrument support | Interface review |
| Attack corpus | Support | Lead | Analysis support | Distributed-mechanism cases |
| Activations | Model interface | Case supply | Lead | Consumer |
| Receiver baseline | Support | Eval | Lead | Compare |
| DCMG/BVP | Trace support | Case supply | Intervention API | Lead |
| Search/RL | Support | Metrics | Lead | DCMG integration |
| Remediation | Runtime | Metrics | Mechanistic support | Lead |
| Statistics | Inputs | Lead | Inputs | Inputs |
| Paper methods | System | Attack/eval | Discovery | Novel method |
| Journal extensions | Systems | Generalization | Advanced search | Defense |
| Patent dossier | Architecture | Evidence | Algorithm details | Lead mechanism |

This table is intended to prevent ambiguous ownership.

---

# 73. Minimum documentation each member maintains

Every member has:

`docs/memberX/weekly_log.md`

Each entry:

```markdown
## Week of YYYY-MM-DD

### Implemented
### Experiments executed
### Quantitative findings
### Failed approaches
### Decisions
### Interfaces changed
### Next week
```

Failed approaches are valuable. Do not delete them from history.

---

# 74. Security and ethics checklist

- local test systems only;
- synthetic/public data;
- no patient identifiers;
- no production MCP servers without authorization;
- no external attack scanning;
- no destructive exploit payloads;
- no credentials committed;
- redact API keys from logs;
- dataset licenses checked;
- model licenses checked;
- disclosure rules reviewed before releasing attack corpus.

The project can study adversarial behavior without operating against real targets.

---

# 75. Final viva preparation questions

Every member must answer:

1. What exact problem does AETHER solve?
2. Why is MCPTox important to your work?
3. Why does MCPTox not make your project redundant?
4. What did MechRL already solve?
5. What exactly did you change beyond MechRL?
6. What is an A2A message node in your graph?
7. How do you claim causality?
8. What is your strongest baseline?
9. What result would falsify H1?
10. What happens if DCMG/BVP is no better than receiver-only or trace/message baselines?
11. How is the defense selected?
12. What is the utility cost?
13. Why medical?
14. Why not a real hospital?
15. Which parts are Phase 1 vs Phase 2?
16. What is potentially patent-relevant?
17. Why are Phase 2 extensions treated as hypotheses/evaluations rather than automatically as novelties?
18. How did AI coding agents affect authorship and validation?
19. How do you know code-generated results are real?
20. Can the project be reproduced?

---

# 76. Recommended final naming discipline

Use one stable project name:

**AETHER**

Avoid changing acronym expansion repeatedly.

Recommended subtitle:

**Intervention-Based Distributed Causal Localization of Adversarial Trust Failures in MCP/A2A Multi-Agent Systems**

For the paper, a shorter title may be better.

Do not force every technology into the title.

---

# 77. Versioning policy

Document versions:

- `0.1` October review;
- `0.5` Phase 1 method freeze;
- `1.0` November 16 release;
- `1.x` Phase 2 updates;
- `2.0` April final release.

Dataset versions independent.

Never reuse an old result after changing:
- model checkpoint;
- attack split;
- metric definition;
- decision parser.

---

# 78. Final operating principle

Generated code is leverage, not evidence.

A strong final-year project is not the repository with the most lines. It is the project where:

- the problem is narrow;
- the method is understood;
- the experiments are controlled;
- the novelty is defensible;
- the results are reproducible;
- the limitations are explicit.

AETHER should be judged on whether it turns an adversarial multi-agent failure into a causally tested mechanism and a targeted remediation decision.

That is the standard every implementation choice in this document is designed to protect.

# 79. Binding benchmark matrix for Phase 1 and Phase 2

This section is binding and overrides any earlier wording that could be interpreted as allowing fully custom evaluation. It is the direct response to the mentor concern that the project must prove capability against recognized data and methods rather than only against a handcrafted demo.

## 79.1 Why a benchmark matrix is required

No single public benchmark validates every layer of AETHER. In particular, existing benchmarks separately cover tool-use competence, MCP poisoning, general multi-agent adversarial risk, known mechanistic circuits, or multi-agent activation signals; they do not provide the exact paired sender-internal / serialized-mediator / receiver-internal intervention dataset needed for the DCMG/BVP hypothesis.

The correct response is **not** to label a project-created dataset "standardized." AETHER uses a **triangulated external-validation stack**:

1. each established sub-capability is tested with an external peer-reviewed benchmark or canonical interpretability task;
2. the exact DCMG/BVP hypothesis is tested on a frozen, transparent project artifact whose source data, attack transformations, splits, hashes, and generation code are released;
3. the project artifact is never reported as an official score for MCPTox, TAMAS, BFCL, PTB-XL, or another external benchmark;
4. closest-method baselines are evaluated on the same AETHER held-out cases so that the novelty test is comparative rather than self-referential.

This structure makes the paper auditable even though no standards organization currently provides a benchmark for the exact internal distributed-causality question.

## 79.2 Phase 1 mandatory benchmark and evidence matrix

| Claim being tested | External benchmark / evidence source | Phase 1 status | Native/standard metric | What AETHER may conclude |
|---|---|---|---|---|
| The chosen open model can perform benign function/tool calling | **BFCL**, pinned evaluator/release | Mandatory | official BFCL AST/execution/relevance metrics as applicable | model/tool competence only |
| MCP tool poisoning is reproducible under a recognized benchmark | **MCPTox AAAI 2026**, pinned paper/repository release | Mandatory | official benchmark ASR/metrics for the exact release | external MCP robustness baseline only |
| The system exhibits adversarial risk in a recognized multi-agent setting | **TAMAS ACL 2026**, official code/data or a clearly labeled open-model reproduction | Mandatory | TAMAS native attack/harmless-task metrics | external multi-agent security anchor only |
| The intervention/discovery code can recover known internal structure | **Tracr** | Mandatory | ground-truth component/path recovery plus behavioral effect | instrumentation correctness / synthetic ground-truth calibration |
| The same code works on a naturally trained transformer with published mechanistic evidence | **IOI or Greater-Than on GPT-2 Small** | Mandatory | canonical task/logit-difference/faithfulness measures and overlap where defined | mechanistic baseline reproduction |
| Sender/message/receiver internal intervention adds value beyond simpler methods | **AETHER-DCMG paired-task artifact**, derived reproducibly from frozen public/synthetic task inputs such as PTB-XL plus frozen attack transformations | Mandatory | predeclared DCMG/BVP metrics; no borrowed "official" score | headline comparative result, if supported |
| Multi-agent internal signals are predictive even without causal intervention | **NARCBench-style probe baseline** on AETHER cases; official NARCBench reproduction if time allows | Baseline mandatory; official external reproduction Tier P1-B | AUROC/PR-AUC/native probe metrics | correlation baseline, not causal evidence |
| Trace/message-level intervention can localize/repair the same failures | **CAR/DoVer/AgentSentry/AttriGuard-style reproducible counterfactual baseline** | Mandatory method baseline | predeclared outcome-change and repair metrics | closest causal-resolution baseline |

Phase 1 is **not paper-ready** until every Mandatory row has: a pinned version or exact implementation description, executable script, immutable result artifact, manifest, and a written statement separating native benchmark results from AETHER adaptations.

### MCPTox version-count rule

The paper record and current public benchmark implementation may expose different case counts because invalid records can be removed in later releases. Record both the paper citation and the exact repository/evaluator commit used. Quote only the count belonging to the reported release. Never merge counts from different versions.

### TAMAS adaptation rule

If the published benchmark configuration uses a model/API incompatible with white-box activation capture, first report the benchmark-compatible result using its native setup where feasible. Any open-weight re-run for AETHER instrumentation is a separate **AETHER open-model reproduction**, with the same task/attack semantics documented and no claim that it is an official leaderboard number.

## 79.3 Phase 2 external-validation matrix

Phase 2 expands external validity rather than replacing the Phase 1 stack.

| Question | External benchmark / extension | Minimum Phase 2 requirement | Why it matters |
|---|---|---|---|
| Does the finding survive a broader cascading-injection benchmark? | **ACIArena ACL 2026** | reproduce a compatible official configuration and, if needed, a separately labeled open-weight instrumented subset | external cascade/MAS generalization |
| Does the causal method add value beyond established multi-agent activation probing? | **NARCBench** | reproduce at least one released/official probe setting and compare predictive evidence with intervention evidence | closest multi-agent interpretability anchor |
| Does the security result transfer outside the custom MCP/A2A harness? | **AgentDojo or InjecAgent** | one full compatible native evaluation or rigorously documented subset | external tool-agent security generalization |
| Does the distributed mechanism survive model heterogeneity? | second open-weight model family | repeat the frozen main experiment with a predeclared model pair | tests X2 / architecture dependence |
| Does mechanism stability survive attack/protocol shift? | frozen MCP and A2A attack families + ACIArena/TAMAS-compatible cases | discover on one condition, test without rediscovery on another | tests X1 rather than re-fitting |
| Does defense preserve repeated tool-agent reliability? | **tau-bench or another state-based tool-agent benchmark**, if technically compatible | optional but recommended | utility/reliability stress test |
| Is the medical harness recipe-specific? | PTB-XL alternate task and/or MIT-BIH secondary validation | optional context check | prevents one exact case-construction recipe from dominating |

External benchmark scores and AETHER's custom causal metrics must remain in separate tables or clearly separated table sections.

## 79.4 Benchmark priority if time becomes constrained

Cut in this order, from first to cut to last to cut:

1. tau-bench;
2. InjecAgent if AgentDojo is already complete;
3. MIT-BIH cross-dataset replication;
4. NARCBench full extension beyond a simple reproduction;
5. second intervention family beyond the required sensitivity check;
6. Phase 2 memory poisoning;
7. second model family only under severe constraints;
8. **never cut BFCL, MCPTox, TAMAS, Tracr/IOI calibration, the mandatory trace/message and receiver-only baselines, or the frozen AETHER-DCMG paired-task artifact test.**

---

# 80. Data provenance, acquisition, and immutable-manifest protocol

The team must be able to answer a reviewer who asks, “Exactly which bytes did you use?”

## 80.1 Directory layout

```text
data/
  external/
    mcptox/
    bfcl/
    tracr/
    ioi/
    ptbxl/
    agentdojo/
    narcbench/
    taubench/
  derived/
    aether_catf_v1/
    aether_catf_v2/
  manifests/
    external_registry.json
    phase1_case_manifest.json
    phase1_attack_manifest.json
    phase1_test_manifest.json
  hashes/
    SHA256SUMS
```

Raw external datasets should be read-only after acquisition.

## 80.2 Dataset acquisition script

Create `scripts/fetch_datasets.py` or shell equivalents that:

- download only public/open resources automatically;
- print manual instructions for resources requiring separate terms;
- verify checksums where upstream provides them;
- compute local SHA256 hashes;
- record release version and retrieval date;
- never overwrite a different version silently.

## 80.3 Derived-data generation

Every derived AETHER-DCMG paired-task artifact file must be reproducible from:

```text
source case ID + source version + transformation config + attack-template ID + random seed + code commit
```

If a generated field cannot be traced to those inputs, it should not be used in a final benchmark artifact.

## 80.4 Dataset cards

Create a dataset card for AETHER-DCMG paired-task artifact containing:

- motivation;
- source datasets;
- licenses;
- construction process;
- task definition;
- split policy;
- attack generation;
- known biases;
- intended use;
- prohibited interpretations;
- limitations;
- ethical considerations;
- statistics by split and attack family;
- version history.

The dataset card should explicitly say that AETHER-DCMG paired-task artifact is not a clinical benchmark and does not validate a medical decision-support system.

## 80.5 Exclusion ledger

Maintain `data/manifests/EXCLUSIONS.csv`:

```text
case_id, benchmark, reason, stage, rule_id, decided_before_test, notes
```

No final exclusion is valid without a rule ID that existed before the final test unless it is an unavoidable infrastructure corruption. Post-hoc exclusions must be disclosed as protocol deviations.

---

# 81. Standardized method stack and baseline ladder

AETHER must use known techniques as anchors before introducing the new method.

## 81.1 Tool/agent behavior stack

Use:

- official MCP SDK/reference implementation where practical;
- official A2A SDK/reference implementation where practical;
- BFCL-compatible structured tool schemas;
- deterministic JSON schemas;
- exact execution or state-based scoring rather than semantic guessing;
- MCPTox-style attack templates for the main MCP attack family;
- AgentDojo native evaluation when external generalization is performed.

## 81.2 Mechanistic-interpretability stack

The technique ladder should be:

1. activation capture;
2. clean/corrupted paired runs;
3. activation patching;
4. zero/mean/resample ablation;
5. random matched-size circuit baseline;
6. greedy causal pruning;
7. established automated-circuit baseline such as ACDC where feasible;
8. MechRL-style RL search or faithful reimplementation;
9. AETHER DCMG/BVP method.

This ordering matters because the paper must show that the DCMG/BVP causal representation adds value beyond simpler internal and trace-level methods; a more complicated search algorithm is not evidence of novelty.

## 81.3 Phase 1 RL rule

RL is mandatory as a Phase 1 baseline but does not automatically become the headline algorithm. The primary research hypothesis concerns incremental causal resolution from explicit distributed mediation; PPO/GRPO/RL remains prior-art search machinery and must earn any primary-method role through matched-budget evidence.

The paper may present:

- greedy DCMG search as the primary method;
- MechRL-style RL as an additional baseline;
- or RL as the primary search if it shows a reproducible benefit.

Do not force RL into the paper because it sounds more advanced.

## 81.4 DCMG construction rule

The DCMG must be explicit about the mediator and separate-execution semantics. At minimum, distinguish:

```text
sender internal nodes
sender output/logit/token nodes
message fields/tokens
receiver input embedding/token nodes
receiver internal nodes
receiver decision/output nodes
```

If the implementation collapses the entire message into one node in Phase 1, state that clearly and treat token-/field-level bridge discovery as a Phase 2 refinement.

## 81.5 Standard causal comparison

Every causal result must include at least:

- clean run;
- attacked run;
- clean-to-attacked patch;
- attacked-to-clean patch;
- discovered-circuit ablation;
- complement ablation or a justified sufficiency test;
- matched random circuit.

This prevents one-direction intervention artifacts from being mistaken for a mechanism.

## 81.6 Probe baseline

Train a linear probe or logistic regression on frozen activations to predict attack success/trust failure. The exact model should remain simple.

Purpose:

- show whether the behavior is linearly decodable;
- compare correlation with causal localization;
- connect to NARCBench-style methodology.

Do not use a complex probe that could memorize examples and then call it interpretability.

---

# 82. Exact Phase 1 final experiment suite under the standardized design

This section should be used to decide whether Phase 1 is complete.

## 82.1 Experiment P1-E0 — Data and evaluator integrity

**Question:** Can the entire data/evaluator stack be reproduced from a clean checkout?

Procedure:

1. create a clean environment;
2. fetch public datasets using scripts;
3. verify hashes;
4. regenerate AETHER-DCMG paired-task artifact manifests from source IDs;
5. run schema validation;
6. verify no test IDs appear in development manifests.

Pass condition:

- all hashes match;
- zero forbidden split overlaps;
- all benchmark/evaluator versions printed in a machine-readable report.

## 82.2 Experiment P1-E1 — Benign capability on BFCL

**Question:** Is the chosen model a competent enough tool user to be a meaningful attack target?

Use the official compatible BFCL categories and evaluator.

Output:

- BFCL result JSON;
- table of official submetrics;
- malformed-call counts;
- exact model revision and prompt/tool formatting.

This result is descriptive; AETHER does not need to beat external models.

## 82.3 Experiment P1-E2 — External attack baseline on MCPTox

**Question:** Does the target model exhibit standardized MCP tool-poisoning susceptibility?

Run the official benchmark or all technically compatible static cases.

Output:

- ASR and official submetrics;
- per-risk-category results;
- exclusions if any;
- raw model responses.

## 82.4 Experiment P1-E3 — Ground-truth mechanistic calibration on Tracr

**Question:** Does the discovery implementation recover a known mechanism?

Run on at least two Tracr programs.

Output:

- component precision/recall/F1;
- faithfulness;
- random baseline;
- graph visualization.

## 82.5 Experiment P1-E4 — Established LLM circuit reproduction

**Question:** Can the project recover a known circuit on GPT-2 Small?

Use IOI or Greater-Than.

Compare:

- random;
- greedy;
- ACDC/established method where practical;
- MechRL-style search.

Output:

- faithfulness-size curve;
- overlap with canonical components;
- compute cost.

## 82.6 Experiment P1-E5 — Clean AETHER-DCMG paired-task artifact baseline

**Question:** Does the target multi-agent pipeline work correctly without attack?

Run locked clean cases.

Output:

- sender tool-use correctness;
- A2A schema validity;
- receiver task accuracy;
- error/timeout rate.

No attack result is interpretable if this baseline is poor.

## 82.7 Experiment P1-E6 — AETHER-DCMG paired-task artifact attack baseline

**Question:** Do the frozen attacks cause measurable targeted failures?

Run all frozen attack families on the exact paired clean cases.

Output:

- unconditional ASR;
- conditional ASR on clean-correct cases;
- per-family ASR;
- refusal/error counts;
- 95% CIs.

## 82.8 Experiment P1-E7 — Receiver-only mechanistic baseline

**Question:** How much of the attacked behavior can be explained by analyzing only the receiver?

Methods:

- receiver probe;
- receiver greedy causal discovery;
- receiver MechRL-style discovery.

Output:

- probe AUROC;
- receiver-only circuit faithfulness;
- size;
- search cost.

## 82.9 Experiment P1-E8 — DCMG/BVP causal localization

**Question:** Does a graph spanning sender, message, and receiver provide a better causal explanation?

Primary comparison:

```text
distributed causal mechanism vs receiver-only circuit at matched size
```

Secondary comparison:

```text
distributed causal mechanism size required to reach the same faithfulness target
```

Output:

- matched-sparsity faithfulness gap;
- faithfulness-size curve;
- bridge-node frequency;
- sender/message/receiver contribution;
- stability across seeds;
- random matched-size percentile.

This is the main Phase 1 scientific result.

## 82.10 Experiment P1-E9 — DCMG-informed intervention

**Question:** Does the discovered circuit identify a better intervention location than fixed defenses?

Compare:

- no defense;
- fixed message sanitation/patch;
- fixed receiver intervention;
- mechanism-guided selected intervention.

Report:

- ASR reduction;
- benign task accuracy;
- tool-use utility;
- false intervention rate;
- latency/compute overhead.

## 82.11 Experiment P1-E10 — Intervention sensitivity

Repeat the key discovery/causal result with a second intervention operator on a representative fixed subset.

Example:

- primary: resample/activation patching;
- sensitivity: zero or mean ablation.

If the main conclusion flips, that must be discussed prominently.

## 82.12 Experiment P1-E11 — Held-out attack generalization

If time permits before paper freeze, discover on one primary attack family and test whether the same mechanism retains explanatory value on a frozen held-out family.

This is a strengthening result, not required for the minimum Phase 1 paper if all core experiments are complete.

---

# 83. Phase 2 standardized-validation expansion through April 2027

Phase 2 exists to convert the Phase 1 mechanism demonstration into a journal/patent-level evidence package.

## 83.1 December — replication and benchmark hardening

Mandatory goals:

- rerun the complete Phase 1 experiment from a clean environment;
- resolve all protocol deviations;
- freeze AETHER-DCMG paired-task artifact v1.1 or v2.0 only if changes are required;
- reproduce one external AgentDojo or InjecAgent baseline;
- reproduce one NARCBench probe using released activations;
- establish the second model family feasibility.

Deliverables:

- reproducibility report;
- external-benchmark appendix draft;
- model-2 feasibility report;
- updated threat-to-validity analysis.

## 83.2 January — model and attack generalization

Run main mechanism discovery on a second model family.

Required comparisons:

- circuit size and faithfulness by model;
- bridge location consistency;
- intervention location consistency;
- attack-family sensitivity;
- whether a circuit from model A transfers in any meaningful way to model B; if not, report non-transfer.

Add memory poisoning only after the second-model replication is underway.

## 83.3 February — defense generalization and reliability

Implement the strongest mechanism-guided remediation strategy chosen from Phase 1 results.

Evaluate:

- external agent-security environment (AgentDojo/InjecAgent);
- benign tool-use regression on BFCL;
- optional tau-bench repeated-trial reliability;
- intervention strength sweep;
- false-positive/false-intervention rate;
- latency and memory overhead.

This month should produce the main Phase 2 defense evidence.

## 83.4 March — journal-scale ablations and robustness

Mandatory:

- two model families;
- multiple attack families;
- multiple intervention operators;
- random, greedy, established automated-circuit and RL baselines;
- full confidence intervals;
- multiple-comparison correction where relevant;
- compute-cost analysis;
- quantization study if edge deployment remains a paper claim;
- at least one cross-dataset or cross-environment result.

All primary tables should be regenerated from frozen result files.

## 83.5 April — paper/patent freeze

No new feature should be added in April unless it repairs a reviewer-critical methodological flaw.

Tasks:

- final independent reproduction by a team member who did not write the module;
- finalize dataset/model cards;
- final literature search for novelty collision;
- create artifact appendix;
- complete invention disclosure and prior-art notes;
- produce Q1-journal manuscript;
- prepare patent material with institutional IP support if still justified.

## 83.6 Patent evidence strengthened by standardized benchmarks

A potential patent narrative is materially stronger if it can show a technical effect across standardized environments.

Record, where supported:

- DCMG-informed intervention reduces standardized attack success;
- benign tool-use benchmark degradation is bounded;
- effect persists across more than one model or attack family;
- intervention requires fewer modified components or lower runtime cost than fixed defense;
- causal verification is used to choose the intervention rather than a generic anomaly score.

Do not state that benchmark superiority proves patentability. It only strengthens evidence of a concrete technical effect.

---

# 84. Mentor/reviewer defense checklist for data and methodology

Before any review, every team member should be able to answer these questions without improvising.

1. **Which standard external attack benchmark do you use?**  
   MCPTox, with a pinned released version and official scoring for the compatible evaluation.

2. **How do you prove the agent can use tools before attacking it?**  
   BFCL-compatible benign function-calling evaluation plus clean AETHER-DCMG paired-task artifact accuracy.

3. **How do you know your circuit-discovery implementation is not producing arbitrary graphs?**  
   Ground-truth calibration on Tracr and reproduction of an established GPT-2 Small circuit task such as IOI/Greater-Than.

4. **Why do you need a new custom dataset at all?**  
   In the bounded literature/benchmark audit used for this project, we did not identify a released benchmark that simultaneously provides paired sender and receiver internal activations, an explicit serialized inter-agent mediator, and the intervention data required for the DCMG/BVP test. Because absence cannot be proved from a bounded search, AETHER does **not** claim to be the first benchmark. The AETHER-DCMG paired-task artifact exists only to evaluate this exact missing combination in our study; it is derived reproducibly from pinned public/synthetic source data such as PTB-XL and frozen attack transformations mapped to external benchmark semantics.

5. **How do you prevent cherry-picking?**  
   Frozen attack families, deterministic case manifests, locked PTB-XL fold 10, predeclared endpoints, and an exclusion ledger.

6. **How do you prove causality rather than correlation?**  
   Paired clean/attacked runs, activation patching/ablation, sufficiency and necessity tests, random matched-size circuits, and held-out evaluation.

7. **How do you prove the distributed method adds value?**  
   Compare DCMG/BVP against receiver-only mechanistic analysis, activation/probe baselines, and trace/message counterfactual attribution under matched or transparently normalized intervention budgets; report compactness and causal quality separately.

8. **How do you prove the defense is not just breaking the agent?**  
   Report benign task accuracy, BFCL regression where appropriate, false intervention rate, and security–utility trade-off alongside ASR.

9. **How do you prove results are reproducible?**  
   Pinned model revisions, benchmark versions, dataset hashes, exact seeds, environment lockfile, immutable raw results, and one-command table generation.

10. **What is the biggest remaining validity limitation?**  
    Phase 1 is a controlled mechanistic study on small open models and a project-created distributed-mechanism paired-task artifact; Phase 2 addresses model, dataset, attack, and external-environment generalization.

---
