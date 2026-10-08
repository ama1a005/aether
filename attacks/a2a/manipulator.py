from typing import List, Dict, Any
from contracts.schemas import A2AMessageRecord, AttackSpec
import copy

class A2AManipulator:
    def __init__(self):
        pass

    def apply_attack(self, message: A2AMessageRecord, attack_spec: AttackSpec) -> A2AMessageRecord:
        if attack_spec.target_surface != 'a2a_message':
            return message
            
        new_msg = A2AMessageRecord.from_dict(message.__dict__.copy())
        new_msg.structured_payload = copy.deepcopy(message.structured_payload or {})
        
        # apply adversarial payload
        for k, v in attack_spec.adversarial_payload.items():
            if k == 'content_text':
                new_msg.content_text = v
            else:
                new_msg.structured_payload[k] = v
                
        new_msg.provenance = copy.deepcopy(message.provenance or {})
        new_msg.provenance['_attack_applied'] = True
        new_msg.provenance['_attack_id'] = attack_spec.attack_id
        new_msg.provenance['_clean_content_text'] = message.content_text
        new_msg.provenance['_clean_structured_payload'] = copy.deepcopy(message.structured_payload)
        
        return new_msg

    def restore_clean(self, message: A2AMessageRecord) -> A2AMessageRecord:
        if not message.provenance.get('_attack_applied'):
            return message
            
        new_msg = A2AMessageRecord.from_dict(message.__dict__.copy())
        new_msg.content_text = message.provenance.get('_clean_content_text', message.content_text)
        new_msg.structured_payload = copy.deepcopy(message.provenance.get('_clean_structured_payload'))
        
        new_msg.provenance = copy.deepcopy(message.provenance)
        new_msg.provenance.pop('_attack_applied', None)
        new_msg.provenance.pop('_attack_id', None)
        new_msg.provenance.pop('_clean_content_text', None)
        new_msg.provenance.pop('_clean_structured_payload', None)
        
        return new_msg

    def get_diff_fields(self, clean: A2AMessageRecord, attacked: A2AMessageRecord) -> List[str]:
        diffs = []
        if clean.content_text != attacked.content_text:
            diffs.append('content_text')
        
        sp_clean = clean.structured_payload or {}
        sp_attacked = attacked.structured_payload or {}
        
        all_keys = set(sp_clean.keys()).union(set(sp_attacked.keys()))
        for k in all_keys:
            if sp_clean.get(k) != sp_attacked.get(k):
                diffs.append(f"structured_payload.{k}")
                
        return diffs
