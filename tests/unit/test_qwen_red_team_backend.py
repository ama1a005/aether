"""Model-free wiring tests for the real-Qwen red-team backend."""

import torch

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
