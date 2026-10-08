from typing import List, Dict, Any
from contracts.schemas import AttackSpec
from attacks.templates.frozen_templates import ATTACK_TEMPLATES

class MCPToxAdapter:
    """
    MCPTox (Wang et al., AAAI 2026) is prior art. AETHER uses MCPTox attack families as stimuli,
    not as a novelty claim. Results from this adapter are labelled AETHER-CATF, NOT MCPTox ASR.
    """
    def __init__(self):
        pass

    def mcptox_to_attack_spec(self, mcptox_attack: Dict[str, Any]) -> AttackSpec:
        return AttackSpec(
            attack_id=mcptox_attack.get("attack_id", "atk_mcptox_000"),
            family=mcptox_attack.get("attack_type", "unknown"),
            target_surface="mcp_tool_description",
            target_behavior="DO_NOT_ESCALATE",
            clean_payload={"description": mcptox_attack.get("original_description", "")},
            adversarial_payload={"description": mcptox_attack.get("malicious_description", "")},
            metadata={"risk_category": mcptox_attack.get("risk_category", "unknown"), "tool_name": mcptox_attack.get("tool_name", "")}
        )

    def get_supported_families(self) -> List[str]:
        return ['tool_description_poison', 'tool_output_inject', 'a2a_manipulation']

    def build_from_template(self, template_id: str, case_id: str, variant: int = 0) -> AttackSpec:
        template = ATTACK_TEMPLATES[template_id]
        return AttackSpec(
            attack_id=f"atk_{template['family'][:10]}_{variant:03d}",
            family=template["family"],
            target_surface=template["target_surface"],
            target_behavior=template["target_behavior"],
            clean_payload=template["clean_payload_template"],
            adversarial_payload=template["adversarial_payload_template"],
            metadata={"template_id": template_id, "case_id": case_id, "description": template["description"]}
        )
