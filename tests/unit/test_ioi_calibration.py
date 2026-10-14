"""Unit tests for IOI calibration invariants."""

import json
from hashlib import sha256
from pathlib import Path

import pytest
import torch

from calibration.ioi.dataset import build_fixed_ioi_dataset
from calibration.ioi.metrics import logit_difference, normalized_recovery


def test_prompt_pairs_are_fixed_unique_and_semantically_consistent() -> None:
    examples = build_fixed_ioi_dataset()
    assert len(examples) == 24
    assert len({example.pair_id for example in examples}) == 24
    for example in examples:
        assert example.subject_name in example.clean_prompt
        assert example.io_name in example.corrupted_prompt
        assert example.clean_prompt != example.corrupted_prompt


def test_logit_difference_uses_io_minus_subject_at_last_position() -> None:
    logits = torch.zeros(2, 3, 7)
    logits[0, -1, 4], logits[0, -1, 2] = 5.0, 1.5
    logits[1, -1, 3], logits[1, -1, 6] = -1.0, 2.0
    result = logit_difference(logits, torch.tensor([4, 3]), torch.tensor([2, 6]))
    assert torch.equal(result, torch.tensor([3.5, -3.0]))


def test_normalized_recovery_formula_and_degenerate_case() -> None:
    assert normalized_recovery(4.0, -2.0, 1.0) == 0.5
    with pytest.raises(ValueError):
        normalized_recovery(1.0, 1.0, 1.0)


def test_reference_circuit_schema_and_head_ranges() -> None:
    data = json.loads(Path("calibration/ioi/reference_circuit.json").read_text(encoding="utf-8"))
    assert data["source_revision"] == "ea15315dd24481e9e2ac5c3ef335d82907a1dc34"
    assert set(data["components"]) == {
        "name mover", "negative", "s2 inhibition", "induction", "duplicate token", "previous token"
    }
    for heads in data["components"].values():
        for layer, head in heads:
            assert 0 <= layer < 12
            assert 0 <= head < 12


def test_completed_calibration_manifest_integrity() -> None:
    manifest_path = Path("results/calibration/ioi/manifest.json")
    if not manifest_path.exists():
        pytest.skip("calibration result is not present in a source-only checkout")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for path_text, expected_hash in manifest["artifact_paths"].items():
        path = Path(path_text)
        assert path.exists()
        assert sha256(path.read_bytes()).hexdigest() == expected_hash
