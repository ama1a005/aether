# TAMAS Official Multi-Agent Adversarial Benchmark Runbook (AETHER Phase 1)

**Benchmark:** TAMAS: Benchmarking Adversarial Risks in Multi-Agent LLM Systems  
**Repository:** `https://github.com/microsoft/TAMAS`  
**Pinned Commit:** `545c112af9aab93b7ef2b0b60831d93c81c365c3`  
**Publication:** arXiv `2511.05269`  
**Licenses:** MIT (code), CDLA-Permissive-2.0 (data)  
**Corpus Geometry:** 300 instances across 6 attack paradigms (50 each for Byzantine, Colluding, Contradicting, DPI, Impersonation, IPI)  
**Native Agent Frameworks:** AutoGen (`pyautogen`) or CrewAI (`crewai`)  
**Provider Configurations:** Local Ollama or API-backed providers (OpenAI, Azure, Anthropic)  

---

## 1. Scientific Context & Novelty Boundary

- **Multi-Agent Attack Paradigms:**
  - *Byzantine:* Erroneous or malicious actions injected arbitrarily by compromised agents.
  - *Colluding:* Multiple malicious agents coordinating secretly to deceive benign agents.
  - *Contradicting:* An agent contradicting consensus to derail group deliberation.
  - *DPI (Direct Prompt Injection):* Attacker interacts directly with agent prompt.
  - *Impersonation:* Malicious agent fakes credentials or role of trusted authority.
  - *IPI (Indirect Prompt Injection):* Untrusted external documents or tool outputs alter agent flow.
- **Novelty Boundary:** Standardized multi-agent adversarial benchmarks are prior art (Microsoft TAMAS, 2025). AETHER does not claim invention of TAMAS; TAMAS provides external standardization for multi-agent adversarial robustness.
- **Independence Contract:** Mechanistic DCMG causal circuits are NOT injected into TAMAS during this sprint. TAMAS is run purely as an independent native external behavioral benchmark.

---

## 2. Evaluation Methods: Rule-Based vs LLM Judge

- **Rule-Based / Deterministic:** Some TAMAS scenarios evaluate outcome state directly (e.g. file modified, unauthorized tool called).
- **LLM Judge:** Other scenarios rely on an automated model judge to grade whether the multi-agent consensus was corrupted.
- **Provenance Discipline:**
  - When LLM judge is used, the exact `judge_model` (e.g. `gpt-4o`, `claude-3-5-sonnet`) and judge prompt version MUST be logged.
  - LLM judge evaluations must never overwrite or replace AETHER's primary objective causal metrics.

---

## 3. Evidence Classes

1. `tamas_official_adapter` (Smoke):
   - Validates data integrity, loads 300 case records.
   - Status: `SMOKE_PASSED`, does not execute multi-agent communication.
   - Never claims `official_protocol: true`.
2. `official_native_subset` (Pilot):
   - Native AutoGen/CrewAI execution of a balanced predeclared subset (e.g. 1 per attack = 6 cases).
   - Clearly labeled as pilot subset.
3. `official_native_execution` (Full):
   - Full 300-case suite on native framework.

---

## 4. Execution Workflow

### Step 4.1: Preflight Verification
```bash
python -c "
from pathlib import Path
from benchmarks.nov19_tamas.preflight import run_tamas_preflight

res = run_tamas_preflight(
    data_root=Path('.cache/benchmarks/TAMAS/data'),
    framework='autogen',
    provider='ollama',
    enforce_framework=False,
)
print('Preflight passed:', res.passed)
print('Details:', res.details)
"
```

### Step 4.2: Running the External Evaluation Script
```bash
python scripts/benchmark_tamas_external_runner.py \
  --data-root .cache/benchmarks/TAMAS/data \
  --output-dir results/phase1/tamas/official \
  --framework autogen \
  --provider ollama \
  --per-attack-count 5 \
  --mode dry-run
```

### Step 4.3: Independent Verification
```bash
python -c "
from pathlib import Path
from benchmarks.nov19_tamas.verifier import TAMASArtifactVerifier

verifier = TAMASArtifactVerifier(Path('results/phase1/tamas/official'))
res = verifier.verify()
print('Verification passed:', res.passed)
print('Metrics:', res.metrics)
"
```
