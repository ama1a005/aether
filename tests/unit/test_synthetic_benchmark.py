import unittest
from causal.validation.synthetic_benchmark import SyntheticCausalBenchmark

class TestSyntheticBenchmark(unittest.TestCase):
    def setUp(self):
        self.bench = SyntheticCausalBenchmark()
        
    def test_ground_truth_nodes(self):
        self.assertEqual(self.bench.get_ground_truth_causal_nodes(), ['S1', 'S2', 'M1', 'R2', 'Y'])
        
    def test_score_drops_with_ablation(self):
        acts = {k: 1.0 for k in self.bench.nodes}
        score = self.bench.compute_score(acts)
        score_s1 = self.bench.compute_score_with_ablation(acts, ['S1'])
        score_m1 = self.bench.compute_score_with_ablation(acts, ['M1'])
        self.assertTrue((score - score_s1) > 0.3)
        self.assertTrue((score - score_m1) > 0.3)
        
    def test_irrelevant_ablation_no_effect(self):
        acts = {k: 1.0 for k in self.bench.nodes}
        score = self.bench.compute_score(acts)
        score_sx = self.bench.compute_score_with_ablation(acts, ['Sx'])
        self.assertTrue(abs(score - score_sx) < 0.01)
        
    def test_precision_recall_perfect(self):
        gt = self.bench.get_ground_truth_causal_nodes()
        res = self.bench.evaluate_recovered_circuit(gt)
        self.assertEqual(res['precision'], 1.0)
        self.assertEqual(res['recall'], 1.0)
        self.assertEqual(res['f1'], 1.0)
        
    def test_precision_recall_partial(self):
        res = self.bench.evaluate_recovered_circuit(['S1', 'M1'])
        self.assertEqual(res['precision'], 1.0)
        self.assertEqual(res['recall'], 2/5)
        
    def test_bridge_localization(self):
        res = self.bench.evaluate_recovered_circuit(['S1', 'M1', 'R2'])
        self.assertEqual(res['bridge_localization_accuracy'], 1.0)

if __name__ == '__main__':
    unittest.main()
