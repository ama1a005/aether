"""Model-free tests for the frozen real-Qwen qualification runner."""

from __future__ import annotations

import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest
import torch

from paired_trace.run_model_qualification import (
    _assert_frozen_inputs,
    _score_valid_messages,
    _validate_model_candidate,
    _verify_snapshot_manifest,
)
from paired_trace.schemas import MediatorMessage


class FakeAdapter:
    """Minimal receiver adapter recording which mediator prompts were scored."""

    def __init__(self) -> None:
        self.prompts: list[str] = []
        self.tokenizer = SimpleNamespace(
            apply_chat_template=lambda messages, **_kwargs: repr(messages)
        )

    def tokenize(self, prompts: list[str]) -> dict[str, torch.Tensor]:
        self.prompts.extend(prompts)
        return {"input_ids": torch.ones((len(prompts), 1), dtype=torch.long)}

    def forward(self, _inputs: dict[str, torch.Tensor]) -> SimpleNamespace:
        logits = torch.zeros((1, 1, 3))
        logits[0, 0, 1] = 4.0
        logits[0, 0, 2] = 0.0
        return SimpleNamespace(logits=logits)


def test_runner_uses_exact_development_registry_and_frozen_hashes() -> None:
    gate, cases, _config = _assert_frozen_inputs()
    assert len(cases) == gate["development_case_count"] == 24
    assert gate["candidate_model_id"] == "Qwen/Qwen2.5-1.5B-Instruct"
    assert {case["split"] for case in cases} == {"development"}
    assert sum(case["attack_direction"] == "A_TO_B" for case in cases) == 12
    assert sum(case["attack_direction"] == "B_TO_A" for case in cases) == 12
    assert len(set(gate["input_hashes"].values())) == 3


def test_invalid_sender_output_is_preserved_but_never_scored_or_repaired() -> None:
    adapter = FakeAdapter()
    messages = [
        MediatorMessage.from_sender_code("case-valid", "A", "frozen evidence"),
        MediatorMessage.from_sender_code("case-invalid", "A plus", "frozen evidence"),
    ]
    result = _score_valid_messages(adapter, messages, {"A": 1, "B": 2}, ["A", "A"])
    assert len(adapter.prompts) == 1
    assert result["predicted"] == ["A", None]
    assert result["scores"] == [4.0, None]
    assert result["input_ids"][1] is None
    assert messages[1].valid is False
    assert messages[1].raw_sender_output == "A plus"


def test_candidate_config_keeps_the_frozen_cpu_float32_policy() -> None:
    candidate = _validate_model_candidate("Qwen/Qwen2.5-1.5B-Instruct")
    assert candidate["revision"] == "989aa7980e4cf806f80c7fef2b1adb7bc71aa306"
    assert candidate["device"] == "cpu"
    assert candidate["dtype"] == "float32"
    assert candidate["quantized"] is False
    assert candidate["low_cpu_mem_usage"] is True


def test_snapshot_manifest_is_rehashed_before_model_load(tmp_path: Path) -> None:
    cache = tmp_path / "hf-cache"
    snapshot = cache / "models--Qwen--Qwen2.5-1.5B-Instruct" / "snapshots" / ("a" * 40)
    snapshot.mkdir(parents=True)
    required = {
        "config.json": b"{}",
        "model.safetensors": b"weights fixture",
        "tokenizer.json": b"{}",
        "tokenizer_config.json": b"{}",
    }
    records = []
    for name, content in required.items():
        path = snapshot / name
        path.write_bytes(content)
        records.append({"path": name, "size": len(content),
                        "sha256": hashlib.sha256(content).hexdigest()})
    manifest = {"resolved_revision": "a" * 40, "snapshot_path": str(snapshot), "files": records}
    _verify_snapshot_manifest(manifest, cache)
    (snapshot / "model.safetensors").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="integrity mismatch"):
        _verify_snapshot_manifest(manifest, cache)
