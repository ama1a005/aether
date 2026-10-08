import numpy as np
from typing import List, Tuple, Callable

class CrossAgentGreedyPruner:
    def __init__(self, graph, score_fn: Callable):
        self.graph = graph
        self.score_fn = score_fn
        self.pruning_history = []

    def prune(self, faithfulness_threshold=0.8) -> tuple:
        retained_nodes = list(self.graph.nodes.keys())
        current_faithfulness = self.score_fn(retained_nodes)
        
        step = 0
        while len(retained_nodes) > 1:
            best_node_to_remove = None
            best_faithfulness = -1.0
            
            for node_id in retained_nodes:
                candidate_nodes = [n for n in retained_nodes if n != node_id]
                score = self.score_fn(candidate_nodes)
                if score >= faithfulness_threshold and score > best_faithfulness:
                    best_faithfulness = score
                    best_node_to_remove = node_id
            
            if best_node_to_remove:
                retained_nodes.remove(best_node_to_remove)
                current_faithfulness = best_faithfulness
                region = self.graph.nodes[best_node_to_remove]["region"]
                self.pruning_history.append((step, best_node_to_remove, len(retained_nodes), current_faithfulness, region))
                step += 1
            else:
                break
                
        return retained_nodes, self.pruning_history

    def compute_random_baseline(self, k: int, n_samples: int, seed: int) -> tuple:
        rng = np.random.default_rng(seed)
        all_nodes = list(self.graph.nodes.keys())
        scores = []
        for _ in range(n_samples):
            sampled = rng.choice(all_nodes, size=min(k, len(all_nodes)), replace=False).tolist()
            scores.append(self.score_fn(sampled))
        return float(np.mean(scores)), float(np.std(scores))

    def faithfulness_size_curve(self) -> List[Tuple[int, float]]:
        curve = []
        for record in self.pruning_history:
            curve.append((record[2], record[3]))
        return curve
