"""Model-free acceptance tests for the real-Qwen QCI runner."""

from __future__ import annotations

import torch

from instrumentation.run_qwen_causal_interventions import (
    _execution_status, _load_inputs, _normalized_score, _qualified_inputs, math_isclose,
)


class _Tokenizer:
    pad_token_id = 99


class _Adapter:
    tokenizer = _Tokenizer()

    @staticmethod
    def tokenize(_prompts: list[str]) -> dict[str, torch.Tensor]:
        return {"input_ids": torch.tensor([[1, 2]])}


def test_frozen_runner_inputs_are_discovery_only_and_complete() -> None:
    base, execution, rows, candidates = _load_inputs()
    assert base["protocol_version"] == "QCI-1.0"
    assert execution["protocol_version"] == "QCI-1.1"
    assert len(rows) == 16 and all(row["split"] == "development" for row in rows)
    assert len(candidates) == 12
    assert {candidate.agent for candidate in candidates} == {"sender", "receiver"}
    node_ids = {f"{candidate.agent}.{candidate.candidate_id}" for candidate in candidates}
    assert len(node_ids) == 12
    assert execution["development_audit"].startswith("forbidden")


def test_qualified_inputs_reconstruct_exact_left_padding() -> None:
    inputs = _qualified_inputs(_Adapter(), "prompt", [99, 99, 1, 2])
    assert inputs["input_ids"].tolist() == [[99, 99, 1, 2]]
    assert inputs["attention_mask"].tolist() == [[0, 0, 1, 1]]


def test_normalized_receiver_score_and_identity_tolerance() -> None:
    logits = torch.zeros((1, 1, 128))
    logits[0, 0, 65], logits[0, 0, 66] = 3.0, 1.0
    assert _normalized_score(logits, {"A": 65, "B": 66}, "A") == 2.0
    assert _normalized_score(logits, {"A": 65, "B": 66}, "B") == -2.0
    tolerance = {"absolute": 1e-6, "relative": 1e-5}
    assert math_isclose(2.00001, 2.0, tolerance)
    assert not math_isclose(2.1, 2.0, tolerance)
    assert _execution_status(1.0, False, 1) == "ok"
    assert _execution_status(1.0, False, 0) == "intervention_application_count_invalid"
    assert _execution_status(1.0, False, 2) == "intervention_application_count_invalid"
    assert _execution_status(1.0, True, 0) == "ok"
    assert _execution_status(None, False, 1) == "invalid_sender_output"
