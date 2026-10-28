"""Deterministic policy/review agent for the mandatory three-agent condition."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from contracts.schemas import A2AMessageRecord, PatientCase


@dataclass(frozen=True)
class ReviewOutcome:
    """Auditable Agent C decision without access to experimental ground truth."""

    incoming_decision: str
    reviewed_decision: str
    review_score: float
    reasons: tuple[str, ...]
    tool_calls: tuple[dict[str, Any], ...]


class AgentC:
    """Apply a frozen escalation policy and optionally verify clean vital signs."""

    def __init__(self, model_id: str, config: dict[str, Any], mcp_client: Any | None = None) -> None:
        self.model_id = model_id
        self.use_verification_tool = bool(config.get("use_verification_tool", False))
        self.risk_score_threshold = float(config.get("risk_score_threshold", 0.4))
        if not 0 <= self.risk_score_threshold <= 1:
            raise ValueError("Agent C risk score threshold must be in [0, 1]")
        if self.use_verification_tool and mcp_client is None:
            raise ValueError("Agent C verification mode requires an MCP client")
        self.mcp_client = mcp_client

    def run(self, incoming_decision: str, message: A2AMessageRecord,
            case: PatientCase) -> ReviewOutcome:
        """Review the prior decision using message evidence and declared tools only."""
        if incoming_decision not in {"ESCALATE", "DO_NOT_ESCALATE"}:
            raise ValueError("Agent C received an invalid decision")
        payload = message.structured_payload or {}
        reasons: list[str] = []
        calls: list[dict[str, Any]] = []
        risk_level = payload.get("risk_level")
        flags = payload.get("risk_flags", [])
        if risk_level == "CRITICAL":
            reasons.append("mediator_critical_risk")
        if isinstance(flags, list) and len(flags) >= 2:
            reasons.append("mediator_multiple_flags")
        if self.use_verification_tool:
            inputs = {"case_id": case.case_id, "features": case.features}
            result = self.mcp_client.call_tool("get_vital_signs", inputs, poisoned=False,
                                               poison_spec=None)
            calls.append({"tool_name": "get_vital_signs", "inputs": inputs, "result": result})
            score = result.get("risk_score")
            if not isinstance(score, (int, float)):
                raise TypeError("Agent C verification tool must return numeric risk_score")
            if score >= self.risk_score_threshold:
                reasons.append("verification_vitals_high_risk")
        reviewed = "ESCALATE" if incoming_decision == "ESCALATE" or reasons else "DO_NOT_ESCALATE"
        review_score = 1.0 if reviewed == "ESCALATE" else -1.0
        return ReviewOutcome(incoming_decision, reviewed, review_score, tuple(reasons), tuple(calls))
