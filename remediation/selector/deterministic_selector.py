from typing import List

class DeterministicInterventionSelector:
    def __init__(self, candidate_evaluations: List[dict]):
        self.candidate_evaluations = candidate_evaluations

    def select(self, min_asr_reduction: float = 0.5) -> dict:
        valid = [c for c in self.candidate_evaluations if c.get("asr_reduction", 0) >= min_asr_reduction]
        if not valid:
            return None
        return min(valid, key=lambda x: x.get("benign_damage", 1.0))

    def pareto_front(self) -> List[dict]:
        front = []
        for cand in self.candidate_evaluations:
            dominated = False
            for other in self.candidate_evaluations:
                if other == cand: continue
                # Dominated if other is better or equal in both objectives, and strictly better in one
                # Maximize asr_reduction, Minimize benign_damage
                asr_better = other.get("asr_reduction", 0) >= cand.get("asr_reduction", 0)
                benign_better = other.get("benign_damage", 1) <= cand.get("benign_damage", 1)
                strict = (other.get("asr_reduction", 0) > cand.get("asr_reduction", 0)) or (other.get("benign_damage", 1) < cand.get("benign_damage", 1))
                if asr_better and benign_better and strict:
                    dominated = True
                    break
            if not dominated:
                front.append(cand)
        return front

    def score_candidate(self, candidate: dict, asr_weight=0.6, utility_weight=0.4) -> float:
        return asr_weight * candidate.get("asr_reduction", 0) - utility_weight * candidate.get("benign_damage", 0)
