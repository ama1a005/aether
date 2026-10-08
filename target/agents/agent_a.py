from typing import Tuple, List, Optional, Dict, Any
import uuid

from contracts.schemas import PatientCase, AttackSpec, A2AMessageRecord
from target.a2a.message_builder import A2AMessageBuilder

class AgentA:
    """The Intake/Evidence Agent"""
    def __init__(self, model_id: str, mcp_client, config: dict):
        self.model_id = model_id
        self.mcp_client = mcp_client
        self.config = config
        self.message_builder = A2AMessageBuilder()

    def run(self, case: PatientCase, attack_spec: Optional[AttackSpec] = None) -> Tuple[str, A2AMessageRecord, List[Dict]]:
        tool_calls = []
        tool_results = []
        
        # Call get_ecg_analysis
        ecg_inputs = {"case_id": case.case_id, "features": case.features}
        ecg_result = self.mcp_client.call_tool(
            tool_name="get_ecg_analysis", 
            inputs=ecg_inputs, 
            poisoned=attack_spec is not None, 
            poison_spec=attack_spec
        )
        tool_calls.append({"tool_name": "get_ecg_analysis", "inputs": ecg_inputs, "result": ecg_result})
        tool_results.append({"tool_name": "get_ecg_analysis", "result": ecg_result})

        # Call get_vital_signs
        vitals_inputs = {"case_id": case.case_id, "features": case.features}
        vitals_result = self.mcp_client.call_tool(
            tool_name="get_vital_signs",
            inputs=vitals_inputs,
            poisoned=attack_spec is not None,
            poison_spec=attack_spec
        )
        tool_calls.append({"tool_name": "get_vital_signs", "inputs": vitals_inputs, "result": vitals_result})
        tool_results.append({"tool_name": "get_vital_signs", "result": vitals_result})

        # Build A2A Message
        run_id = f"run_{case.case_id}_{'attacked' if attack_spec else 'clean'}"
        attack_id = attack_spec.attack_id if attack_spec else None
        
        message = self.message_builder.build(
            run_id=run_id,
            sender=self.model_id,
            receiver="agent_b_model",
            case=case,
            tool_results=tool_results,
            attack_id=attack_id
        )

        agent_output_text = f"Intake complete for {case.case_id}. A2A message prepared: {message.content_text}"

        return agent_output_text, message, tool_calls
