import torch
import csv
from typing import List, Dict, Any, Tuple, Callable

class GreedyCausalPruner:
    def __init__(self, model, hook_registry, intervention_operator, faithfulness_fn, 
                 candidate_nodes: List[str], faithfulness_threshold: float = 0.8,
                 target_fn: Callable = None):
        self.model = model
        self.hook_registry = hook_registry
        self.intervention_operator = intervention_operator
        self.faithfulness_fn = faithfulness_fn
        self.candidate_nodes = candidate_nodes
        self.faithfulness_threshold = faithfulness_threshold
        self.target_fn = target_fn

    def prune(self, attacked_examples, clean_examples) -> Tuple[List[str], List[Tuple[int, int, float]]]:
        # For simplicity, assuming batch size 1 and list of tensors
        input_ids = attacked_examples[0] # taking first example for now, ideally loop
        
        # Calculate full effect
        with torch.no_grad():
            clean_out = self.model(clean_examples[0])
            adv_out = self.model(input_ids)
            
        clean_score = self.target_fn(clean_out) if self.target_fn else clean_out.item()
        adv_score = self.target_fn(adv_out) if self.target_fn else adv_out.item()
        delta_full = adv_score - clean_score
        
        retained = list(self.candidate_nodes)
        history = []
        step = 0
        
        # Initial faithfulness
        history.append((step, len(retained), 1.0))
        
        while len(retained) > 1:
            best_node = None
            best_f = -1.0
            
            for node in retained:
                test_set = [n for n in retained if n != node]
                # apply intervention to ALL OTHER NODES except test_set
                # i.e., we zero ablate the nodes not in test_set
                ablated = [n for n in self.candidate_nodes if n not in test_set]
                out, _ = self.intervention_operator(self.model, input_ids, ablated)
                score = self.target_fn(out) if self.target_fn else out.item()
                delta_c = score - clean_score
                f = self.faithfulness_fn(delta_full, delta_c)
                
                if f > best_f:
                    best_f = f
                    best_node = node
                    
            if best_f >= self.faithfulness_threshold:
                retained.remove(best_node)
                step += 1
                history.append((step, len(retained), best_f))
            else:
                break
                
        # Benign damage
        out, _ = self.intervention_operator(self.model, clean_examples[0], [n for n in self.candidate_nodes if n not in retained])
        score_after = self.target_fn(out) if self.target_fn else out.item()
        self.benign_damage = abs(clean_score - score_after)
        
        # Save to csv
        with open('results/raw/p3_smoke_intervention_results.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['step', 'n_retained', 'faithfulness'])
            writer.writerows(history)
            
        return retained, history
