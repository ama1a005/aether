from causal.metrics.faithfulness import compute_faithfulness, compute_necessity, compute_benign_damage
import pytest

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


def test_faithfulness_preserves_wrong_direction_and_overshoot():
    assert compute_faithfulness(1.0, -1.0) == pytest.approx(1 - 2 / 1.000001)
    assert compute_faithfulness(1.0, 3.0) < 0
    assert compute_faithfulness(-1.0, 1.0) < 0


@pytest.mark.parametrize("full,circuit,eps", [(float("nan"), 1, 1e-6), (1, float("inf"), 1e-6), (1, 1, 0)])
def test_invalid_faithfulness_inputs_fail_closed(full, circuit, eps):
    with pytest.raises(ValueError):
        compute_faithfulness(full, circuit, eps)
