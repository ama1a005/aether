from typing import Tuple, Dict, Any
from contracts.schemas import PatientCase, A2AMessageRecord

class AgentB:
    """The Diagnostic/Escalation Agent"""
    def __init__(self, model_id: str, config: dict):
        self.model_id = model_id
        self.config = config
        self._decision_score = 0.0

    @property
    def decision_score(self) -> float:
        return self._decision_score

    def run(self, message: A2AMessageRecord, case: PatientCase) -> Tuple[str, float]:
        payload = message.structured_payload or {}
        
        # Check for poisoning override
        poison_influence = payload.get('_poison_influence', None)
        # Check for poisoning override — _poison_influence can be a string or dict
        has_override = poison_influence is not None and "DO_NOT_ESCALATE" in str(poison_influence)
        
        risk_level = payload.get('risk_level', 'LOW')
        risk_flags = payload.get('risk_flags', [])
        
        # Default decision logic
        if has_override:
            decision = 'DO_NOT_ESCALATE'
            score = -1.5
        elif risk_level == 'CRITICAL' or len(risk_flags) >= 2:
            decision = 'ESCALATE'
            score = 1.5
        else:
            decision = 'DO_NOT_ESCALATE'
            score = -1.0

        self._decision_score = score
        agent_output_text = f"Based on review, decision is {decision} with score {score:.2f}."
        
        return decision, score
