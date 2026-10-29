"""Explicit rule-based acceptance backend; never a real-model fallback."""
from copy import deepcopy
from dataclasses import asdict
from typing import Callable

from attacks.orchestration import FAMILY_SURFACES, Recon
from contracts.schemas import AttackSpec, PatientCase, RunTrace
from target.agents.agent_a import AgentA
from target.agents.agent_b import AgentB
from target.mcp.tools import get_ecg_analysis, get_vital_signs


class RuleBasedBackend:
    """Run existing A/B rules with literal payload injection and raw traces.

    Description text is exposed as context without adding an override token.
    This preserves implicit attacks as implicit text; rule agents may ignore it.
    An optional tool executor supports separately constructed local MCP clients.
    """

    def __init__(self, tool_executor: Callable[[str, dict], dict] | None = None,
                 transport_id: str = "in_process_functions") -> None:
        self.tool_executor = tool_executor
        self.transport_id = transport_id

    def discover(self) -> Recon:
        """Report explicit rule-model identity and supported local surfaces."""
        return Recon(f"rule_based:{self.transport_id}", "aether_rule_agents", "v1",
                     "not_applicable", "synthetic_software_acceptance_only",
                     tuple(sorted(set(FAMILY_SURFACES.values()))), tuple(
                         {"name": name, "inputSchema": {"type": "object", "required": ["case_id", "features"]}}
                         for name in ("get_ecg_analysis", "get_vital_signs")))

    def execute(self, case: PatientCase, attack: AttackSpec | None, seed: int) -> RunTrace:
        """Execute tool calls, sender aggregation, optional message patch and receiver."""
        tools = {"get_ecg_analysis": get_ecg_analysis, "get_vital_signs": get_vital_signs}
        executor = self.tool_executor

        class Client:
            def call_tool(self, tool_name, inputs, poisoned=False, poison_spec=None):
                result = (executor(tool_name, inputs) if executor else tools[tool_name](**inputs))
                if not isinstance(result, dict):
                    raise TypeError("Rule backend requires structured tool objects")
                result = deepcopy(result)
                # Restrict tool attacks to the declared ECG tool.
                if poison_spec and tool_name == "get_ecg_analysis":
                    payload = poison_spec.adversarial_payload
                    if not isinstance(payload, dict):
                        raise ValueError("Rule backend requires an object attack payload")
                    if poison_spec.target_surface == "mcp_tool_description":
                        result["_poison_context"] = payload["description"]
                    elif poison_spec.target_surface == "mcp_tool_output":
                        result = deepcopy(payload.get("result", payload))
                return result

        sender = AgentA("rule_agent_a", Client(), {})
        _, message, calls = sender.run(case, attack)
        if attack and attack.target_surface == "a2a_message":
            payload = attack.adversarial_payload
            if not isinstance(payload, dict) or set(payload) - {"content_text", "risk_level", "risk_flags"}:
                raise ValueError("Unsupported A2A patch fields")
            for field, value in payload.items():
                if field == "content_text":
                    message.content_text = value
                else:
                    message.structured_payload[field] = deepcopy(value)
        decision, score = AgentB("rule_agent_b", {}).run(message, case)
        return RunTrace(message.run_id, case.case_id, seed,
                        {"agent_a": "rule_agent_a", "agent_b": "rule_agent_b"},
                        [asdict(message)], calls, decision,
                        attack.attack_id if attack else None, score)
