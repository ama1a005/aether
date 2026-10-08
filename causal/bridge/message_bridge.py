import json
from typing import List, Tuple

class MessageBridge:
    def __init__(self):
        self.sender_message_links: List[Tuple[str, str, float]] = []
        self.message_receiver_links: List[Tuple[str, str, float]] = []

    def estimate_sender_to_message_attribution(
        self, sender_activations_clean: dict, sender_activations_attacked: dict,
        message_clean: dict, message_attacked: dict
    ) -> List[Tuple[str, str, float]]:
        # Simple correlation-based attribution (mean abs diff in sender activations vs message token diff)
        # Mock logic to avoid deep NN dependencies, assuming clean/attacked are dicts of components -> floats
        links = []
        for comp_id, val_c in sender_activations_clean.items():
            val_a = sender_activations_attacked.get(comp_id, 0.0)
            diff_a = abs(val_c - val_a)
            for msg_node_id in message_clean:
                # Assign arbitrary score based on difference
                links.append((comp_id, msg_node_id, diff_a * 0.1))
        self.sender_message_links = links
        return links

    def estimate_message_to_receiver_attribution(
        self, message_variants: dict, receiver_score_fn
    ) -> List[Tuple[str, str, float]]:
        # Patch message fields one at a time and measure receiver score change
        links = []
        base_score = receiver_score_fn(message_variants.get("clean", {}))
        for msg_node_id, patched_msg in message_variants.items():
            if msg_node_id == "clean": continue
            score = receiver_score_fn(patched_msg)
            diff = abs(base_score - score)
            links.append((msg_node_id, "receiver_in", diff))
        self.message_receiver_links = links
        return links

    def to_dict(self) -> dict:
        return {
            "sender_message_links": self.sender_message_links,
            "message_receiver_links": self.message_receiver_links
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'MessageBridge':
        mb = cls()
        mb.sender_message_links = d.get("sender_message_links", [])
        mb.message_receiver_links = d.get("message_receiver_links", [])
        return mb
