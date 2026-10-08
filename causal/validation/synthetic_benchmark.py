from typing import List

class SyntheticCausalBenchmark:
    def __init__(self):
        self.nodes = {
            'S1': {'val': 1.0, 'region': 'sender'},
            'S2': {'val': 1.0, 'region': 'sender'},
            'Sx': {'val': 1.0, 'region': 'sender'},
            'M1': {'val': 1.0, 'region': 'message'},
            'Mx': {'val': 1.0, 'region': 'message'},
            'R2': {'val': 1.0, 'region': 'receiver'},
            'Rx': {'val': 1.0, 'region': 'receiver'},
            'Y': {'val': 1.0, 'region': 'outcome'}
        }
        
    def get_ground_truth_causal_nodes(self) -> List[str]:
        return ['S1', 'S2', 'M1', 'R2', 'Y']
        
    def get_ground_truth_bridge_nodes(self) -> List[str]:
        return ['M1']
        
    def compute_score(self, node_activations: dict) -> float:
        # Score = f(S1) * g(M1) * h(R2)
        s1 = node_activations.get('S1', 0.0)
        m1 = node_activations.get('M1', 0.0)
        r2 = node_activations.get('R2', 0.0)
        return float(s1 * m1 * r2)
        
    def compute_score_with_ablation(self, node_activations: dict, ablated_nodes: List[str]) -> float:
        acts = dict(node_activations)
        for n in ablated_nodes:
            acts[n] = 0.0
        return self.compute_score(acts)
        
    def build_candidate_graph(self):
        from causal.candidate_graph.cross_agent_graph import CrossAgentGraph
        g = CrossAgentGraph()
        for nid, meta in self.nodes.items():
            g.add_node({"id": nid, "type": "layer", "region": meta['region'], "retained": True, "metadata": {}})
        
        # Add edges (S1 -> S2, S2 -> M1, M1 -> R2, R2 -> Y)
        g.add_edge({"src": "S1", "dst": "S2", "type": "internal", "bridge": False, "weight": 1.0})
        g.add_edge({"src": "S2", "dst": "M1", "type": "sender_to_message", "bridge": True, "weight": 1.0})
        g.add_edge({"src": "M1", "dst": "R2", "type": "message_to_receiver", "bridge": True, "weight": 1.0})
        g.add_edge({"src": "R2", "dst": "Y", "type": "to_outcome", "bridge": False, "weight": 1.0})
        
        return g
        
    def evaluate_recovered_circuit(self, recovered_node_ids: List[str]) -> dict:
        from causal.validation.metrics import precision, recall, f1, bridge_localization_accuracy, false_positive_rate
        gt = self.get_ground_truth_causal_nodes()
        all_cands = list(self.nodes.keys())
        return {
            "precision": precision(recovered_node_ids, gt),
            "recall": recall(recovered_node_ids, gt),
            "f1": f1(recovered_node_ids, gt),
            "bridge_localization_accuracy": bridge_localization_accuracy(recovered_node_ids, self.get_ground_truth_bridge_nodes()),
            "false_positive_rate": false_positive_rate(recovered_node_ids, gt, all_cands)
        }
