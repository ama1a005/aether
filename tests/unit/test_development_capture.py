"""Model-free checks for prospective Qwen development capture."""

from __future__ import annotations

import torch

from instrumentation.run_qwen_development_capture import (
    _capture_one,
    _load_inputs,
    _paired_measurements,
)


def test_capture_partitions_are_disjoint_balanced_and_development_only() -> None:
    config, rows = _load_inputs()
    assert len(rows) == 20
    assert len(config["discovery_case_ids"]) == 16
    assert len(config["development_audit_case_ids"]) == 4
    partitions = [
        set(config["excluded_acceptance_case_ids"]),
        set(config["discovery_case_ids"]),
        set(config["development_audit_case_ids"]),
    ]
    assert set.intersection(*partitions) == set()
    assert len(set.union(*partitions)) == 24
    assert all(row["split"] == "development" and row["eligible"] for row in rows)
    for key in ("discovery_case_ids", "development_audit_case_ids"):
        selected = [row for row in rows if row["case_id"] in config[key]]
        assert sum(row["direction"] == "A_TO_B" for row in selected) == len(selected) // 2


def test_paired_measurements_are_complete_finite_and_not_ranked() -> None:
    clean = {
        "module.L0.mlp_output": torch.tensor([[1.0, 0.0]]),
        "head.L0.pre_o_proj_heads": torch.tensor([[[1.0], [2.0]]]),
    }
    attacked = {
        "module.L0.mlp_output": torch.tensor([[0.0, 1.0]]),
        "head.L0.pre_o_proj_heads": torch.tensor([[[2.0], [1.0]]]),
    }
    rows = _paired_measurements(clean, attacked)
    assert [row["component_id"] for row in rows] == sorted(clean)
    assert all(row["l2_distance"] > 0 for row in rows)
    assert all(-1.0 <= row["cosine_similarity"] <= 1.0 for row in rows)
    assert all("rank" not in row for row in rows)


class _FakeTokenizer:
    pad_token_id = 99

    @staticmethod
    def decode(_tokens: list[int], skip_special_tokens: bool = True) -> str:
        del skip_special_tokens
        return "A"


class _FakeOutput:
    def __init__(self) -> None:
        self.logits = torch.zeros((1, 4, 128))
        self.logits[0, -1, 65] = 1.0


class _FakeCaptureAdapter:
    def __init__(self) -> None:
        self.tokenizer = _FakeTokenizer()
        self.activations: dict[str, torch.Tensor] = {}
        self.head_activations: dict[str, torch.Tensor] = {}
        self._handles: list[object] = []
        self.forwarded: dict[str, torch.Tensor] | None = None

    def tokenize(self, _prompts: list[str]) -> dict[str, torch.Tensor]:
        return {"input_ids": torch.tensor([[1, 2]])}

    def identify_components(self, _layers: list[int]) -> list[object]:
        return []

    def install_comprehensive_capture(self, _sites: list[object], _layers: list[int]) -> None:
        self.activations = {"L0.mlp_output": torch.ones((1, 4, 2))}

    def forward(self, inputs: dict[str, torch.Tensor]) -> _FakeOutput:
        self.forwarded = inputs
        return _FakeOutput()

    def remove_hooks(self) -> None:
        self._handles.clear()


def test_capture_reconstructs_qualified_left_padded_input(tmp_path) -> None:
    adapter = _FakeCaptureAdapter()
    _payload, record = _capture_one(
        adapter, "prompt", [99, 99, 1, 2],
        {"layers": [0], "module_components": [], "token_position": -1},
        tmp_path / "capture.pt", {"A": 65, "B": 66}, "A", "receiver",
    )
    assert adapter.forwarded is not None
    assert adapter.forwarded["input_ids"].tolist() == [[99, 99, 1, 2]]
    assert adapter.forwarded["attention_mask"].tolist() == [[0, 0, 1, 1]]
    assert record["input_token_ids"] == [99, 99, 1, 2]
    assert record["left_padding_token_count"] == 2


def test_capture_rejects_prompt_content_token_mismatch(tmp_path) -> None:
    adapter = _FakeCaptureAdapter()
    try:
        _capture_one(
            adapter, "prompt", [99, 1, 3],
            {"layers": [0], "module_components": [], "token_position": -1},
            tmp_path / "capture.pt", {"A": 65, "B": 66}, "A", "receiver",
        )
    except ValueError as error:
        assert str(error) == "capture tokenization differs from qualified prompt token IDs"
    else:
        raise AssertionError("content token mismatch was accepted")
