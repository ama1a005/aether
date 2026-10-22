import torch
import math

def compute_target_score(logits: torch.Tensor, decision_tokens: dict) -> float:
    # decision_tokens: {'unsafe': id1, 'safe': id2}
    unsafe_id = decision_tokens['unsafe']
    safe_id = decision_tokens['safe']
    
    # logits shape might be (batch, seq, vocab) or (vocab,)
    if logits.dim() > 1:
        logits = logits[0, -1, :] # assume single batch, last token
        
    return float((logits[unsafe_id] - logits[safe_id]).item())

def compute_attack_effect(attacked_score: float, clean_score: float) -> float:
    return attacked_score - clean_score

def compute_faithfulness(delta_full: float, delta_circuit: float, eps: float = 1e-6) -> float:
    """Apply the frozen formula without hiding negative recovery by clipping."""
    if not all(math.isfinite(value) for value in (delta_full, delta_circuit, eps)) or eps <= 0:
        raise ValueError("Faithfulness inputs must be finite and epsilon positive")
    return 1.0 - abs(delta_full - delta_circuit) / (abs(delta_full) + eps)

def compute_necessity(score_full: float, score_ablated: float) -> float:
    return score_full - score_ablated

def compute_benign_damage(clean_score_before: float, clean_score_after: float) -> float:
    return abs(clean_score_before - clean_score_after)
