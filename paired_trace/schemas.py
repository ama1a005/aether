"""Additive paired-trace schemas; frozen shared contracts remain unchanged."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json
from typing import Any, Literal

SCHEMA_VERSION = "aether.mediator.v1"
ALLOWED_ATTACK_DELTA_FIELDS = frozenset({"tool_evidence.recommendation_code"})


def canonical_json(value: dict[str, Any]) -> str:
    """Serialize deterministically as compact UTF-8 JSON with sorted keys."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


@dataclass(frozen=True)
class MediatorMessage:
    """Frozen structured message transported from sender to receiver."""

    schema_version: str
    case_id: str
    decision_code: Literal["A", "B"]
    evidence: str
    source: str
    confidence: float
    raw_sender_output: str
    valid: bool = True
    parse_error: str | None = None

    def serialize(self) -> str:
        """Return canonical mediator JSON, preserving raw model output."""
        return canonical_json(asdict(self))

    def sha256(self) -> str:
        """Hash the exact serialized UTF-8 mediator bytes."""
        return sha256(self.serialize().encode("utf-8")).hexdigest()

    @classmethod
    def from_sender_code(cls, case_id: str, code: str, evidence: str) -> "MediatorMessage":
        """Parse an exact A/B sender code without silent repair."""
        stripped = code.strip()
        valid = stripped in {"A", "B"}
        return cls(
            schema_version=SCHEMA_VERSION,
            case_id=case_id,
            decision_code=stripped if valid else "B",
            evidence=evidence,
            source="get_ecg_analysis",
            confidence=1.0,
            raw_sender_output=code,
            valid=valid,
            parse_error=None if valid else "sender output must be exactly A or B",
        )


@dataclass(frozen=True)
class ConditionTrace:
    """One clean or attacked sender-message-receiver execution."""

    condition: Literal["clean", "attacked"]
    sender_prompt: str
    sender_output: str
    message: MediatorMessage
    message_token_ids: list[int]
    receiver_prompt: str
    receiver_code: str
    receiver_decision: str
    score: float
    activation_refs: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class PairedTrace:
    """Linked clean/attacked real-model runs for one controlled task."""

    pair_id: str
    task_id: str
    split: Literal["development", "validation", "test"]
    ground_truth: str
    seed: int
    model_id: str
    model_revision: str
    tokenizer_revision: str
    attack_family: str
    declared_attack_delta: dict[str, Any]
    shared_environment: dict[str, Any]
    clean: ConditionTrace
    attacked: ConditionTrace
    eligible: bool
    eligibility_reason: str
    result_type: Literal["real_model"] = "real_model"

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible trace representation."""
        return asdict(self)


def validate_pair_inputs(clean: dict[str, Any], attacked: dict[str, Any]) -> None:
    """Fail closed unless only the declared attack field differs."""
    clean_copy = json.loads(json.dumps(clean))
    attacked_copy = json.loads(json.dumps(attacked))
    clean_code = clean_copy["tool_evidence"].pop("recommendation_code")
    attacked_code = attacked_copy["tool_evidence"].pop("recommendation_code")
    if clean_copy != attacked_copy:
        raise ValueError("unexpected clean/attack structural difference")
    if clean_code == attacked_code:
        raise ValueError("declared attack field did not change")


def validate_attack_delta(delta: dict[str, Any]) -> None:
    """Reject attack specifications outside the frozen one-field whitelist."""
    if set(delta) != ALLOWED_ATTACK_DELTA_FIELDS:
        raise ValueError("attack delta must modify only tool_evidence.recommendation_code")
