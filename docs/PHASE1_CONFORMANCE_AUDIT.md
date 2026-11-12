# Phase 1 conformance audit

**State:** QCI-1 executed and independently verified, but no candidate passed
its case-specific rule and QCI-A1 is forbidden. A confirmed control-
identifiability gap is addressed by a separately frozen QCI-2 study using
same-decision and opposite-decision donors; it has not executed. Real Qwen
qualification, instrumentation acceptance and development capture pass.
Every Phase 1 feature is mandatory. Phase 2 is separate.

| Requirement | Implemented | Remaining acceptance |
|---|---|---|
| Target/MCP/Agent C | Deterministic A/B/C, SDK MCP boundary, explicit failures | Qualified Qwen and live external MCP campaign |
| Attacks/red team | Four-family corpus, bounded orchestration, raw manifests | Real Qwen development campaign and frozen eligibility |
| Causal mechanisms | Cross-agent graph; node/head/SAE/message/path replay; QCI-1.1 completed with 0/12 case-specific candidates; QCI-2 frozen | Execute QCI-2; N1 remains unestablished; QCI-A1 forbidden |
| Qwen adapter | Pre-`o_proj` layer/head capture and patch; IA-G1 PASS; 1,376 QCI-1 executions valid | QCI-2 same/opposite-decision controls require retained execution |
| SAE | Hashed checkpoint, provenance, normalization, error gate | Pinned trained SAE matched to Qwen |
| Search/RL | Greedy, beam, random, receiver/full, fully observed PPO | Real matched multi-seed and ablations |
| Statistics/report | Paired CIs/McNemar/seeds/errors and gated reports | Final tables from complete qualified runs |
| Benchmarks | PTB-XL adapter; pinned BFCL/AgentDojo interfaces; disclosed Qwen2.5 BFCL adapter; MCPTox/TAMAS imports | Execute official evaluators and retain immutable artifacts |
| Reproducibility/CI | Configs, manifests, policy checks, transfer preflight, 20-gate completion audit | Remaining real-run manifests and remote CI record |
| Second model | Extensible interfaces | Select, pin and qualify another architecture |

Current tests prove software behavior on constructed inputs only. They do not
prove Qwen competence, causal validity, benchmark scores or generalization.
Historical negative results remain unchanged. Locked splits remain inaccessible.

The QCI negative result is scientifically usable and must be reported, but it
means the current frozen Qwen path cannot supply the headline internal-circuit,
matched-search or mechanism-guided-remediation evidence. It must not be turned
into a positive result by post-hoc threshold or candidate changes.

Known-structure Tracr and GPT-2 IOI causal calibrations now pass. Current
verification: Python 3.11.9, **401 passed and 5 gated skips** (382 unit plus 19
integration/regression passes); regression tests execute every existing smoke
command. `python scripts/audit_phase1_completion.py` remains intentionally
nonzero until every mandatory evidence gate is satisfied. Root
`PROJECT_STATE.md` is the authoritative remaining-work record.
