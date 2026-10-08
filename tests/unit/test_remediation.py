import unittest
from remediation.candidates.extractor import RemediationCandidateExtractor
from remediation.selector.deterministic_selector import DeterministicInterventionSelector

class MockGraph:
    def __init__(self):
        self.nodes = {
            "1": {"type": "layer", "region": "sender"},
            "2": {"type": "message_field", "region": "message"},
            "3": {"type": "layer", "region": "receiver"}
        }

class TestRemediation(unittest.TestCase):
    def test_candidate_extraction(self):
        ext = RemediationCandidateExtractor(MockGraph())
        cands = ext.extract_candidates()
        self.assertEqual(len(cands), 3)
        self.assertEqual(cands[0]['region'], 'message')
        self.assertTrue(cands[0]['estimated_causal_strength'] >= cands[1]['estimated_causal_strength'])
        
    def test_selector_min_asr(self):
        evals = [
            {"id": "1", "asr_reduction": 0.4, "benign_damage": 0.1},
            {"id": "2", "asr_reduction": 0.6, "benign_damage": 0.5},
            {"id": "3", "asr_reduction": 0.8, "benign_damage": 0.9},
        ]
        sel = DeterministicInterventionSelector(evals)
        best = sel.select(min_asr_reduction=0.5)
        self.assertEqual(best["id"], "2")
        
    def test_pareto_front(self):
        evals = [
            {"id": "1", "asr_reduction": 0.5, "benign_damage": 0.1},
            {"id": "2", "asr_reduction": 0.6, "benign_damage": 0.3},
            {"id": "3", "asr_reduction": 0.4, "benign_damage": 0.2}, # dominated by 1
        ]
        sel = DeterministicInterventionSelector(evals)
        front = sel.pareto_front()
        self.assertEqual(len(front), 2)
        ids = [f["id"] for f in front]
        self.assertIn("1", ids)
        self.assertIn("2", ids)

if __name__ == '__main__':
    unittest.main()
