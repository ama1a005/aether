from typing import List

def precision(predicted: List[str], ground_truth: List[str]) -> float:
    if not predicted: return 0.0
    correct = len(set(predicted) & set(ground_truth))
    return float(correct / len(predicted))

def recall(predicted: List[str], ground_truth: List[str]) -> float:
    if not ground_truth: return 0.0
    correct = len(set(predicted) & set(ground_truth))
    return float(correct / len(ground_truth))

def f1(predicted: List[str], ground_truth: List[str]) -> float:
    p = precision(predicted, ground_truth)
    r = recall(predicted, ground_truth)
    if p + r == 0: return 0.0
    return float(2 * p * r / (p + r))

def bridge_localization_accuracy(predicted: List[str], ground_truth_bridges: List[str]) -> float:
    if not ground_truth_bridges: return 0.0
    correct = len(set(predicted) & set(ground_truth_bridges))
    return float(correct / len(ground_truth_bridges))

def false_positive_rate(predicted: List[str], ground_truth: List[str], all_candidates: List[str]) -> float:
    negatives = set(all_candidates) - set(ground_truth)
    if not negatives: return 0.0
    false_positives = set(predicted) & negatives
    return float(len(false_positives) / len(negatives))

def jaccard_similarity(set_a: List[str], set_b: List[str]) -> float:
    sa, sb = set(set_a), set(set_b)
    if not sa and not sb: return 1.0
    return float(len(sa & sb) / len(sa | sb))
