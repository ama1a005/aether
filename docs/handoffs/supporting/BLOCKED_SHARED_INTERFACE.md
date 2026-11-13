# BLOCKED_SHARED_INTERFACE.md — Shared Interface Change Assessment

**Branch:** `amala`  
**Author:** Friend B — supporting-experiments lead  
**Date:** 2026-11-13

---

## Summary

After completing SUPPORT-00 through SUPPORT-04 scaffold implementation and reviewing
all public APIs consumed by the supporting experiments, **no shared-interface
modifications are required**.

All four supporting experiments (red-team, Agent C, SAE, second-model) work
exclusively through the existing frozen APIs:

| API / Module | Import Pattern | Modification Needed? |
|---|---|---|
| `contracts/schemas.py` | `from contracts.schemas import PatientCase, AttackSpec, RunTrace` | **No** |
| `attacks/orchestration.py` | `from attacks.orchestration import CampaignConfig, run_campaign, Recon, plan_campaign` | **No** |
| `attacks/corpus/attack_store.py` | `from attacks.corpus.attack_store import AttackStore` | **No** |
| `attacks/corpus/builder.py` | `from attacks.corpus.builder import CorpusBuilder` | **No** |
| `attacks/backends.py` | `from attacks.backends import RuleBasedBackend` | **No** |
| `target/agents/agent_a.py` | `from target.agents.agent_a import AgentA` | **No** |
| `target/agents/agent_b.py` | `from target.agents.agent_b import AgentB` | **No** |
| `target/agents/agent_c.py` | `from target.agents.agent_c import AgentC` | **No** |
| `target/mcp/mock_client.py` | `from target.mcp.mock_client import MockMCPClient` | **No** |
| `target/runner.py` | `from target.runner import run_pair` | **No** |
| `target/three_agent_pipeline.py` | `from target.three_agent_pipeline import run_three_agent_pipeline` | **No** |
| `causal/interventions/sae.py` | `from causal.interventions.sae import load_sae_checkpoint, SAEProvenance` | **No** |
| `instrumentation/model_adapter.py` | `from instrumentation.model_adapter import load_model_and_tokenizer` | **No** |
| `instrumentation/adapters/qwen2.py` | `from instrumentation.adapters.qwen2 import Qwen2Adapter` | **No** |

## Known Compatibility Notes

1. **`MockMCPClient` constructor**: Accepts `tools: Optional[Dict[str, Callable]]` only;
   does NOT accept a `label=` keyword argument. Tools must be registered via
   `mcp.register_tool("name", fn)` after construction.

2. **`AgentA` / `AgentB` constructors**: Accept optional `model=` and `tokenizer=`
   kwargs for real-model mode. The mock/fixture path works without them.

3. **`AgentC` constructor**: Does not accept `model=` / `tokenizer=` kwargs. It uses
   deterministic policy by default. Optional `mcp_client=` for verification tool path.

## Discovered Issues

None. No shared-interface changes were blocked or deferred.

## Recommendation

If future experiments require schema extensions (e.g., new fields on `PatientCase`
or `RunTrace`), file a schema-change issue with Friend A before modifying any frozen
contract file. Use extension fields in `metadata: Dict[str, Any]` for experiment-local
data until the schema change is approved.
