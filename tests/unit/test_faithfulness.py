from causal.metrics.faithfulness import compute_faithfulness, compute_necessity, compute_benign_damage

def test_faithfulness_perfect():
    assert compute_faithfulness(1.0, 1.0) == 1.0

def test_faithfulness_zero():
    # Formula uses eps=1e-6 to guard division by zero, so result is near-zero not exactly zero.
    # F(C) = 1 - |1.0 - 0.0| / (|1.0| + 1e-6) ≈ near 0
    result = compute_faithfulness(1.0, 0.0)
    assert result < 0.01, f"Expected faithfulness near 0, got {result}"

def test_necessity_effect():
    assert compute_necessity(5.0, 3.0) == 2.0

def test_benign_damage():
    assert compute_benign_damage(1.0, 0.5) == 0.5
