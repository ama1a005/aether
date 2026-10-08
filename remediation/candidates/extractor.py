from typing import List

class RemediationCandidateExtractor:
    def __init__(self, graph):
        self.graph = graph

    def extract_candidates(self) -> List[dict]:
        candidates = []
        for node_id, node in self.graph.nodes.items():
            # Mock estimation of causal strength, e.g., higher for messages, maybe based on metadata
            strength = 0.5
            if node["region"] == "message":
                strength = 0.9
            elif node["region"] == "sender":
                strength = 0.7
            
            candidates.append({
                "candidate_id": f"cand_{node_id}",
                "location_type": node["type"],
                "component_id": node_id,
                "region": node["region"],
                "estimated_causal_strength": strength,
                "intervention_operators": ["ablate", "patch"]
            })
        
        # Sort by causal strength descending
        candidates.sort(key=lambda x: x["estimated_causal_strength"], reverse=True)
        return candidates
