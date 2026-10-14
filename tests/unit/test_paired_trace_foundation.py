"""Unit tests for paired real traces and Bridge Verification Protocol foundations."""

from dataclasses import asdict
import json

import pytest
import torch

from paired_trace.bvp import BVPEvidence, EvidenceLevel, maximum_verified_level
from paired_trace.metrics import (
    escalation_margin,
    mediation_recovery,
    validate_label_tokens,
    validate_token_alignment,
)
from paired_trace.run_foundation import _save_last_token_artifact
from paired_trace.schemas import (
    MediatorMessage,
    canonical_json,
    validate_attack_delta,
    validate_pair_inputs,
)
from paired_trace.splits import frozen_splits, require_development, split_hash


def _input(code: str) -> dict[str, object]:
    return {
        "task_id": "ecg_000",
        "features": {"heart_rate": 120},
        "tool_evidence": {"recommendation_code": code, "tool_name": "get_ecg_analysis"},
    }


def test_pair_validator_accepts_only_declared_attack_field() -> None:
    validate_pair_inputs(_input("A"), _input("B"))
    attacked = _input("B")
    attacked["features"] = {"heart_rate": 80}
    with pytest.raises(ValueError, match="unexpected"):
        validate_pair_inputs(_input("A"), attacked)


def test_attack_delta_whitelist_fails_closed() -> None:
    validate_attack_delta({"tool_evidence.recommendation_code": {"clean": "A", "attacked": "B"}})
    with pytest.raises(ValueError, match="only"):
        validate_attack_delta({"features.heart_rate": {"clean": 120, "attacked": 80}})


def test_message_schema_serialization_and_invalid_handling() -> None:
    first = MediatorMessage.from_sender_code("ecg_000", "A", "evidence")
    second = MediatorMessage.from_sender_code("ecg_000", "A", "evidence")
    assert first.valid and first.serialize() == second.serialize()
    assert first.sha256() == second.sha256()
    payload = json.loads(first.serialize())
    assert canonical_json(payload) == first.serialize()
    invalid = MediatorMessage.from_sender_code("ecg_000", "A because", "evidence")
    assert not invalid.valid
    assert invalid.parse_error is not None


def test_logit_margin_sign_convention() -> None:
    logits = torch.zeros(2, 1, 5)
    logits[0, -1, 2], logits[0, -1, 3] = 4.0, 1.0
    logits[1, -1, 2], logits[1, -1, 3] = -2.0, 2.0
    margins = escalation_margin(logits, {"A": 2, "B": 3})
    assert torch.equal(margins, torch.tensor([3.0, -4.0]))


def test_outcome_labels_require_distinct_single_tokens() -> None:
    class Tokenizer:
        def __init__(self, tokens: dict[str, list[int]]) -> None:
            self.tokens = tokens

        def encode(self, label: str, add_special_tokens: bool = False) -> list[int]:
            assert not add_special_tokens
            return self.tokens[label]

    assert validate_label_tokens(Tokenizer({"A": [32], "B": [33]})) == {"A": 32, "B": 33}
    with pytest.raises(ValueError, match="not a single token"):
        validate_label_tokens(Tokenizer({"A": [1, 2], "B": [3]}))
    with pytest.raises(ValueError, match="same token"):
        validate_label_tokens(Tokenizer({"A": [4], "B": [4]}))


def test_recovery_is_unclipped_and_rejects_degenerate_denominator() -> None:
    assert mediation_recovery(4.0, -2.0, 1.0) == 0.5
    assert mediation_recovery(4.0, -2.0, 7.0) == 1.5
    assert mediation_recovery(4.0, -2.0, -5.0) == -0.5
    with pytest.raises(ValueError, match="too small"):
        mediation_recovery(1.0, 1.0 + 1e-9, 1.0)


def test_split_integrity_hash_and_locked_test_protection() -> None:
    ids = [f"pair_{index:03d}" for index in range(24)]
    splits = frozen_splits(ids)
    assert {key: len(value) for key, value in splits.items()} == {
        "development": 16, "validation": 4, "test": 4
    }
    assert len(split_hash(splits)) == 64
    require_development("pair_000", splits)
    with pytest.raises(PermissionError, match="locked"):
        require_development("pair_023", splits)


def test_sender_receiver_namespaces_are_separate() -> None:
    sender = {"sender.L12.mlp_output": torch.ones(1)}
    receiver = {"receiver.L12.mlp_output": torch.ones(1)}
    assert set(sender).isdisjoint(receiver)


def test_cached_activation_artifact_records_hash_shape_and_provenance(tmp_path) -> None:
    path = tmp_path / "sender.pt"
    metadata = _save_last_token_artifact(
        path, "sender", {"L4.mlp_output": torch.arange(24).reshape(2, 3, 4)}
    )
    payload = torch.load(path, weights_only=True)
    assert metadata["provenance"] == "real_model"
    assert metadata["token_position"] == "last_prompt_token"
    assert metadata["shapes"] == {"sender.L4.mlp_output": [2, 1, 4]}
    assert len(metadata["sha256"]) == 64
    assert torch.equal(payload["sender.L4.mlp_output"], torch.tensor([[[8, 9, 10, 11]], [[20, 21, 22, 23]]]))


def test_token_alignment_requires_equal_lengths_and_valid_position() -> None:
    assert validate_token_alignment([1, 2, 3], [1, 9, 3]) == 2
    with pytest.raises(ValueError, match="lengths"):
        validate_token_alignment([1, 2], [1, 2, 3])
    with pytest.raises(ValueError, match="outside"):
        validate_token_alignment([1], [2], position=2)


def test_bvp_rejected_evidence_does_not_promote_level() -> None:
    records = [
        BVPEvidence("M-Y", EvidenceLevel.MEDIATOR_CAUSAL, "accepted", "swap", ("p",), 1.0, 1.0, "x", "real_model"),
        BVPEvidence("A-M", EvidenceLevel.SENDER_TO_MEDIATOR, "rejected", "patch", ("p",), 0.0, 0.0, "x", "real_model"),
    ]
    assert maximum_verified_level(records) == EvidenceLevel.MEDIATOR_CAUSAL
    assert asdict(records[0])["result_type"] == "real_model"


def test_synthetic_and_real_provenance_are_not_aggregated() -> None:
    records = [
        BVPEvidence("x", EvidenceLevel.ASSOCIATION, "accepted", "diff", ("p",), None, None, "x", "synthetic"),
        BVPEvidence("y", EvidenceLevel.ASSOCIATION, "accepted", "diff", ("p",), None, None, "x", "real_model"),
    ]
    groups = {kind: [r for r in records if r.result_type == kind] for kind in {r.result_type for r in records}}
    assert set(groups) == {"synthetic", "real_model"}
