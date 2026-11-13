# AETHER Core Architecture & Scientific Foundations: Benchmark Lead Study Notes

**Author:** Friend A — Independent Benchmark Lead (Antigravity, Laptop 2)  
**File:** `docs/handoffs/benchmarks/STUDY_NOTES.md`  
**Date:** 2026-11-13  
**Status:** COMPLETE (Ground truth: `RESEARCH_CONTRACT.md`, `Phase1Project.md`, `PROJECT_STATE.md`)  

---

## Part 1: Conceptual Foundations (The 10 Required Points)

### 1. Clean $\rightarrow$ Attacked $\rightarrow$ Mediator $\rightarrow$ Receiver Decision Pipeline
- **Upstream Agent A (Sender):** Consumes clinical case record / tool output (`SCP-ECG` structured data derived deterministically from PTB-XL). Produces a serialized structured message `AgentMessage` containing:
  - `sender_id`: Agent A identifier
  - `recommendation`: Decision prompt recommendation (`ESCALATE` or `DO_NOT_ESCALATE`)
  - `clinical_justification`: Structured text rationale
  - `confidence`: Confidence score
  - `case_id`: PTB-XL record identifier
- **Intervention Boundary (Mediator):** Serialized text/JSON transmission where message fields can be intervened upon (e.g., token replacement, field modification).
- **Downstream Agent B (Receiver):** Ingests `AgentMessage`, generates activation traces, and outputs final decision:
  - Decision code: `A` (Escalate to cardiologist) or `B` (Do not escalate)
  - Logit margin: $T(x) = \text{logit}(A) - \text{logit}(B)$

### 2. Attack Control: Tool-Result Recommendation vs MCPTox Metadata Poisoning
- **AETHER ECG Positive Control:** Modifies the *tool execution result* (changing the diagnostic recommendation in returned tool data). The model processes a manipulated observation.
- **MCPTox Tool-Metadata Poisoning:** Modifies the *tool description during registration* in the tool catalog/server specification. The model is tricked by tool descriptions/prerequisites into calling legitimate server tools with attacker-crafted arguments.

### 3. MCP vs A2A vs Serial Message Data Contracts
- **MCP (Model Context Protocol):** Client-server protocol standardizing how LLMs discover and invoke external tools, resources, and prompts. In production, tools are exposed over JSON-RPC.
- **A2A (Agent-to-Agent):** Inter-agent protocol defining schemas for structured peer communication, delegation, and verification.
- **Serial Message:** The concrete string/JSON payload transmitted over wire or in-memory. AETHER operates at the tokenized representation of this serialized message.

### 4. Distributed Causal Mechanism Graph (DCMG) vs Single Neural Circuit
- A classical neural circuit (e.g., IOI circuit in GPT-2) operates within a single continuous neural network across attention heads and MLPs.
- **DCMG:** A heterogeneous directed acyclic graph spanning:
  1. Internal activation nodes of Sender Agent A ($A_i$)
  2. Discursive/lexical nodes of the mediator message ($M_j$)
  3. Internal activation nodes of Receiver Agent B ($B_k$)
  4. Final decision output node ($Y$)
- The two agents do not share a single continuous computational graph; they interact via discrete serialized token distributions, requiring cross-boundary causal bridge formalisms.

### 5. Activation Patching vs Correlation; QCI-1 vs QCI-2
- **Correlational Evidence:** An internal probe or linear representation predicts the attack outcome. This does not prove causal necessity or sufficiency.
- **Causal Evidence (Required):** Intervening on the internal component (patching activation from clean into attacked, or vice versa) alters the downstream decision logit margin $\Delta$.
- **QCI-1:** Case-specific internal mediation discovery (observed 0/12 candidates supported in development baseline).
- **QCI-2:** Decision-semantic intervention discovery (observed 4/12 candidate support; discovers generalizable semantic intervention points).

### 6. Baselines: Search & Causal Baselines vs Headline Novelty
- Random search, greedy node deletion, beam search, PPO, and receiver-only ablations are *standard search algorithms and baseline comparisons*.
- AETHER's novelty is NOT inventing RL or greedy search; its core novelty is the **formalism of cross-boundary distributed causal circuits (DCMG) and Bridge Verification Protocol (BVP)**.

### 7. Validation Discipline and Locked-Test Ethics
- Folds 1–8 of PTB-XL are for development/discovery.
- Fold 9 is for protocol validation.
- Fold 10 is the **LOCKED TEST SPLIT**: accessed once and only once at the conclusion of Phase 1.
- Tuning hyperparameters, selecting prompts, or choosing circuit thresholds on Fold 10 is strictly prohibited. External benchmarks (BFCL, MCPTox, TAMAS) have their own official evaluation sets and must NEVER access or contaminate AETHER's locked clinical test split.

### 8. Attack Success Rate, Denominators, and Failure Modes
- $\text{ASR} = \frac{\text{Successful Targeted Attacks}}{\text{Eligible Attack Attempts}}$
- Eligibility is fixed *before* observing model outputs.
- In MCPTox: Total $N = 485$, Scored = $N - \text{None}$, where `None` indicates unparseable/missing tool calls. Errors and non-responses are never silently dropped.
- Failure modes: `Failure-Ignored`, `Failure-Direct Execution`, `Failure-Refused`, `Error/Timeout`.

### 9. External Benchmark Evidence Hierarchy
1. *Adapter Unit Test:* Tests parsing on mock fixtures.
2. *Released-Response Smoke:* Re-scores published model outputs from the dataset release.
3. *Official Evaluator with Disclosed Model Adapter:* Official test suite executed on a registered custom model adapter with open disclosure.
4. *Native Official Execution:* Unmodified official benchmark pipeline executed in native framework.

### 10. Key Limitations of Phase 1
- Simplified binary decision code ($A/B$).
- Cohort size limited to qualified open-weight model (`Qwen2.5-1.5B-Instruct`).
- External benchmarks require qualified compute (CUDA/vLLM) and are blocked locally on CPU-only hardware.
- Scientific gates remain marked missing until genuine executed evidence is verified.

---

## Part 2: 15 Viva Voce Questions & Authoritative Answers

**Q1: What is the primary scientific hypothesis of AETHER?**  
*Answer:* That adversarial trust failures across autonomous agents are mediated by a distributed, identifiable causal circuit spanning sender internal activations, message tokens, and receiver activations, which can be discovered via cross-boundary intervention and used to guide targeted repairs better than message-only or receiver-only defenses.

**Q2: Why does AETHER require activation patching rather than probing?**  
*Answer:* Linear probes only detect correlation between internal states and outcomes; they cannot distinguish causal mechanisms from epiphenomena or passive downstream representations. Activation patching demonstrates causal counterfactual necessity and sufficiency.

**Q3: How does BFCL relate to AETHER's causal claims?**  
*Answer:* BFCL does not prove DCMG causality. It proves benign tool-use competence. Without BFCL, a reviewer could argue that Agent A's susceptibility to tool manipulation is merely an artifact of an incompetent model that cannot execute function calling even under benign conditions.

**Q4: Why is registering `AETHER/Qwen2.5-1.5B-Instruct-FC` in BFCL considered a disclosed adapter rather than native leaderboard performance?**  
*Answer:* The official `bfcl_eval` 2026.3.23 package ships model handlers for Qwen 1.5/2.0 but does not natively configure Qwen2.5. We added the custom registry entry. Labeling it as an unmodified leaderboard entry would be scientifically dishonest; disclosing the adapter maintains rigorous provenance.

**Q5: What is the exact difference between the AETHER ECG attack and MCPTox?**  
*Answer:* The AETHER ECG attack manipulates observation data returned in tool execution outputs. MCPTox poisons tool metadata descriptions during registration to trick the agent into executing unauthorized actions on other server tools.

**Q6: What are the three released attack paradigms in MCPTox?**  
*Answer:* Template-1 (unrelated prerequisites), Template-2 (fake enabling prerequisites), and Template-3 (argument hijacking).

**Q7: Why does MCPTox exclude `None` from the ASR denominator?**  
*Answer:* Following the official AAAI 2026 paper and released evaluation notebook, `None` denotes instances where the model failed to generate valid tool calls or produced empty output, leaving $N - \text{None}$ as the validly attempted tool-use cohort.

**Q8: Why can we not commit full MCPTox raw records to GitHub?**  
*Answer:* The pinned repository at commit `f85189f9` lacks an explicit open-source LICENSE file. Redistributing raw records could violate intellectual property rights. We preserve hashes, provenance, and small aggregate statistics.

**Q9: What are the six attack categories evaluated in TAMAS?**  
*Answer:* Byzantine, Colluding, Contradicting, Direct Prompt Injection (DPI), Impersonation, and Indirect Prompt Injection (IPI), with 50 cases each (300 total).

**Q10: Why is running TAMAS cases through AETHER's two-agent harness considered `aether_transformed` rather than native TAMAS?**  
*Answer:* Native TAMAS specifies AutoGen or CrewAI multi-agent conversation frameworks. Substituting AETHER's custom two-agent harness alters the execution topology, interaction dynamics, and communication protocols, making it a transformed cross-check rather than native execution.

**Q11: When is an LLM judge permitted in AETHER evaluations?**  
*Answer:* Never on primary objective endpoints where deterministic labels exist. In TAMAS where multi-agent consensus grading requires subjective assessment, LLM judges are permitted only if the judge model, revision, prompt, and exact score criteria are disclosed.

**Q12: What was the finding of QCI-1, and why was it not a failure of the project?**  
*Answer:* QCI-1 found 0/12 candidate support for case-specific internal activation mediation. This was an honest negative result showing that internal mediation in this model was not purely instance-specific, directly motivating QCI-2 which discovered decision-semantic intervention points (4/12 support).

**Q13: Why is writing a mock `summary.json` with `overall: PASS` prohibited even if it makes the completion audit pass?**  
*Answer:* Syntactically satisfying a completion gate without executing the prescribed empirical protocol is scientific fraud. The project rules mandate that gates remain MISSING or BLOCKED until real verified evidence exists.

**Q14: Why do we use Wilson score confidence intervals rather than Wald intervals?**  
*Answer:* Wald intervals ($\hat{p} \pm z\sqrt{\hat{p}(1-\hat{p})/n}$) collapse to a zero-width interval when $\hat{p}=0$ or $\hat{p}=1$, and suffer severe coverage errors for small sample sizes. Wilson score intervals invert the score test and provide robust coverage even at extreme proportions.

**Q15: What is the Bridge Verification Protocol (BVP)?**  
*Answer:* BVP is the formal verification protocol in AETHER that tests whether intervening on an upstream sender activation alters the transmitted message tokens, and whether patching those altered message tokens subsequently shifts downstream receiver activations and final decision logits.

---

## Part 3: 5 Critical Methodological Pitfalls to Avoid

1. **The Synthetic Substitution Fallacy:** Assuming that testing on AETHER's synthetic ECG tool tampering proves resistance to metadata poisoning like MCPTox.
2. **Denominator Loss / Survivor Bias:** Dropping timeouts, formatting errors, or nonresponses from benchmark denominators, falsely inflating accuracy or attack success rates.
3. **The Unlabeled Model Adapter Trap:** Running a custom model adapter in an official evaluation tool (like BFCL) and reporting the score as an official leaderboard submission without disclosing the registration adapter.
4. **LLM Judge Hallucination / Drift:** Using an unpinned, proprietary LLM judge to determine attack success without recording exact prompt versions, temperatures, and model checkpoint revisions.
5. **Premature Gate Closure:** Creating placeholder artifact files to turn completion audit scripts green before genuine external compute campaigns have executed and been verified.

---

## Part 4: Complete Worked Example: Valid Benchmark Result Interpretation

### Scenario
An external benchmark run of MCPTox (Template-1) is conducted on `Qwen/Qwen2.5-1.5B-Instruct` across 77 eligible cases.

### Raw Observations
- Total cases attempted: 77
- Validly generated responses: 74
- Model timeouts / API errors: 3
- Model outputs classified as `Success` (malicious server tool called): 14
- Model outputs classified as `Failure-Ignored` (benign query answered safely): 52
- Model outputs classified as `Failure-Direct Execution` (poisoned tool called directly): 5
- Model outputs classified as `Failure-Refused` (safety refusal): 3
- Unparseable / empty outputs (`None`): 0

### Calculation
1. **Total Denominator:** $N_{\text{total}} = 77$
2. **Scored Denominator:** $N_{\text{scored}} = 77 - 0 = 77$
3. **Attack Success Rate (ASR):** $\text{ASR} = \frac{14}{77} \approx 0.1818$ (18.18%)
4. **95% Wilson Confidence Interval:**
   $$\text{Lower} = 0.1118, \quad \text{Upper} = 0.2801 \quad \implies [11.2\%, 28.0\%]$$
5. **Errors Retained:** 3 errors logged explicitly ($3/77 = 3.90\%$).

### Valid Paper Reporting Statement
> "Under the official-compatible MCPTox Template-1 evaluation (unrelated prerequisite metadata poisoning), `Qwen2.5-1.5B-Instruct` exhibited an Attack Success Rate of 18.18% (14/77, 95% Wilson CI [11.2%, 28.0%]). 67.53% of cases (52/77) successfully ignored the malicious directive, 6.49% (5/77) directly executed the poisoned tool, 3.90% (3/77) refused on ethical grounds, and 3.90% (3/77) encountered execution timeouts. This confirms baseline susceptibility to metadata poisoning under authentic MCP tool schemas. This behavioral rate establishes external vulnerability but does not, by itself, isolate the internal cross-agent causal circuit; that analysis is performed under the Bridge Verification Protocol (BVP)."
