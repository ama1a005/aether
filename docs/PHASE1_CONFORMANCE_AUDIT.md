# Phase 1 conformance audit

**State:** implementation is complete to the model-independent boundary;
real-model and external-data acceptance remain open. Every Phase 1 feature is
mandatory. Phase 2 is separate.

| Requirement | Implemented | Remaining acceptance |
|---|---|---|
| Target/MCP/Agent C | Deterministic A/B/C, SDK MCP boundary, explicit failures | Qualified Qwen and live external MCP campaign |
| Attacks/red team | Four-family corpus, bounded orchestration, raw manifests | Real Qwen development campaign and frozen eligibility |
| Causal mechanisms | Cross-agent graph; node/head/SAE/message/path replay | Real capture, specificity controls and accepted circuits |
| Qwen adapter | Pre-`o_proj` layer/head capture and patch | Real checkpoint non-interference/interventions |
| SAE | Hashed checkpoint, provenance, normalization, error gate | Pinned trained SAE matched to Qwen |
| Search/RL | Greedy, beam, random, receiver/full, fully observed PPO | Real matched multi-seed and ablations |
| Statistics/report | Paired CIs/McNemar/seeds/errors and gated reports | Final tables from complete qualified runs |
| Benchmarks | PTB-XL adapter; BFCL/AgentDojo plans; MCPTox/TAMAS imports | Pin compatibility, freeze subsets, native execution |
| Reproducibility/CI | Configs, manifests, policy checks, transfer preflight | Remote CI and larger-machine record |
| Second model | Extensible interfaces | Select, pin and qualify another architecture |

Current tests prove software behavior on constructed inputs only. They do not
prove Qwen competence, causal validity, benchmark scores or generalization.
Historical negative results remain unchanged. Locked splits remain inaccessible.

Current verification: Python 3.11.9, **333 passed and 5 gated skips**; regression
tests execute every existing smoke command. Root `PROJECT_STATE.md` is the
authoritative remaining-work record.
