import uuid
from typing import List, Dict, Optional
from contracts.schemas import A2AMessageRecord, PatientCase

class A2AMessageBuilder:
    def build(self, run_id: str, sender: str, receiver: str, case: PatientCase, tool_results: List[Dict], attack_id: Optional[str] = None) -> A2AMessageRecord:
        
        # Aggregate tool results
        ecg_summary = {}
        risk_level = "LOW"
        risk_flags = []
        tools_used = []
        poison_influence = None
        
        for tr in tool_results:
            name = tr.get('tool_name', '')
            tools_used.append(name)
            res = tr.get('result', {})
            
            if name == 'get_ecg_analysis':
                ecg_summary = res
                risk_level = res.get('risk_level', 'LOW')
                if 'flags' in res:
                    risk_flags.extend(res['flags'])
                    
            if '_poison_context' in res:
                poison_influence = res['_poison_context']
            elif name == 'get_ecg_analysis' and '_poison_influence' in res: # fallback if embedded
                poison_influence = res['_poison_influence']
            elif attack_id and 'DO_NOT_ESCALATE' in str(res):
                 poison_influence = "DO_NOT_ESCALATE"

        content_text = f"Review for Case {case.case_id}. Risk Level: {risk_level}. Flags: {', '.join(risk_flags) if risk_flags else 'None'}."
        if poison_influence:
            content_text += f" Note: {poison_influence}"

        structured_payload = {
            "case_id": case.case_id,
            "ecg_summary": ecg_summary,
            "risk_level": risk_level,
            "risk_flags": list(set(risk_flags)),
            "tool_used": tools_used,
            "agent_confidence": 0.9
        }
        
        if poison_influence is not None:
            structured_payload["_poison_influence"] = poison_influence
            
        provenance = {
            "tool_call_ids": [str(uuid.uuid4()) for _ in tool_results],
            "attack_id": attack_id,
            "sender_model": sender
        }

        return A2AMessageRecord(
            message_id=str(uuid.uuid4()),
            run_id=run_id,
            sender=sender,
            receiver=receiver,
            content_text=content_text,
            structured_payload=structured_payload,
            provenance=provenance
        )
