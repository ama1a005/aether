import pandas as pd
from typing import Callable

class CrossAgentInterventionRunner:
    def __init__(self, graph, intervention_fn, message_record, receiver_score_fn, receiver_intervention_fn):
        self.graph = graph
        self.intervention_fn = intervention_fn
        self.message_record = message_record
        self.receiver_score_fn = receiver_score_fn
        self.receiver_intervention_fn = receiver_intervention_fn
        self.intervention_records = []

    def run_message_patch(self, attacked_message: dict, clean_message: dict, field_path: str = None) -> tuple:
        score_before = self.receiver_score_fn(attacked_message)
        patched = dict(attacked_message)
        if field_path:
            patched[field_path] = clean_message.get(field_path)
        else:
            patched = dict(clean_message)
        score_after = self.receiver_score_fn(patched)
        self.intervention_records.append({
            "intervention_location": "message",
            "component_id": field_path or "full",
            "score_before": score_before,
            "score_after": score_after,
            "delta": score_after - score_before,
            "is_causal": abs(score_after - score_before) > 0.05
        })
        return (score_before, score_after)

    def run_sender_intervention(self, component_id: str, operator: str, clean_activations: dict) -> tuple:
        score_before = self.receiver_score_fn(self.message_record)
        patched_msg = self.intervention_fn(component_id, operator, clean_activations)
        score_after = self.receiver_score_fn(patched_msg)
        self.intervention_records.append({
            "intervention_location": "sender",
            "component_id": component_id,
            "score_before": score_before,
            "score_after": score_after,
            "delta": score_after - score_before,
            "is_causal": abs(score_after - score_before) > 0.05
        })
        return (score_before, score_after)

    def run_receiver_intervention(self, component_id: str, operator: str, clean_activations: dict, attacked_message: dict) -> tuple:
        score_before = self.receiver_score_fn(attacked_message)
        score_after = self.receiver_intervention_fn(component_id, operator, clean_activations, attacked_message)
        self.intervention_records.append({
            "intervention_location": "receiver",
            "component_id": component_id,
            "score_before": score_before,
            "score_after": score_after,
            "delta": score_after - score_before,
            "is_causal": abs(score_after - score_before) > 0.05
        })
        return (score_before, score_after)

    def compare_intervention_locations(self) -> pd.DataFrame:
        return pd.DataFrame(self.intervention_records)
