"""Model-free wiring tests for the real-Qwen red-team backend."""

import torch
import pytest

from attacks.qwen_backend import QwenRedTeamBackend
from contracts.schemas import AttackSpec, PatientCase


class Tokenizer:
    def apply_chat_template(self, messages, tokenize, add_generation_prompt):
        return str(messages)
    def decode(self, token_ids, skip_special_tokens=True):
        return "A" if token_ids == [1] else "B"


class Adapter:
    model = object()
    tokenizer = Tokenizer()
    def __init__(self, outputs): self.outputs = iter(outputs)
    def tokenize(self, prompts): return {"input_ids": torch.tensor([[9, 9]])}
    def generate_uncached(self, inputs, count): return torch.tensor([[9, 9, next(self.outputs)]])


def test_qwen_backend_runs_literal_message_attack_and_preserves_provenance() -> None:
    backend = QwenRedTeamBackend(Adapter([1, 2]), model_id="qwen", model_revision="rev")
    case = PatientCase("c", {"heart_rate": 130}, "ESCALATE", source_split="development")
    attack = AttackSpec("a", "a2a_manipulation", "a2a_message", "DO_NOT_ESCALATE", {},
                        {"risk_level": "LOW", "content_text": "benign"})
    trace = backend.execute(case, attack, 7)
    assert trace.final_decision == "DO_NOT_ESCALATE" and trace.attack_id == "a"
    assert trace.model_ids == {"agent_a": "qwen", "agent_b": "qwen"}
    assert trace.messages[0]["structured_payload"]["risk_level"] == "LOW"


def test_qwen_backend_accepts_frozen_registry_decimal_strings() -> None:
    backend = QwenRedTeamBackend(Adapter([1, 1]), model_id="qwen", model_revision="rev")
    case = PatientCase("c", {"heart_rate": 80, "st_deviation_mv": "0.4"},
                       "ESCALATE", source_split="development")
    trace = backend.execute(case, None, 7)
    assert trace.tool_calls[0]["result"]["risk_level"] == "CRITICAL"
    assert trace.tool_calls[0]["result"]["heart_rate"] == 80.0


def test_qwen_backend_rejects_non_numeric_registry_fields() -> None:
    backend = QwenRedTeamBackend(Adapter([1, 1]), model_id="qwen", model_revision="rev")
    case = PatientCase("c", {"heart_rate": 80, "st_deviation_mv": "not-a-number"},
                       "ESCALATE", source_split="development")
    with pytest.raises(TypeError, match="st_deviation_mv must be numeric"):
        backend.execute(case, None, 7)
