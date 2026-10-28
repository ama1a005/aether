"""Additive three-agent orchestration preserving the two-agent baseline."""

from __future__ import annotations

from dataclasses import dataclass

from contracts.schemas import AttackSpec, PatientCase
from target.agents.agent_a import AgentA
from target.agents.agent_b import AgentB
from target.agents.agent_c import AgentC, ReviewOutcome


@dataclass(frozen=True)
class ThreeAgentResult:
    """Raw outputs from all three declared pipeline stages."""

    agent_a_output: str
    agent_b_decision: str
    agent_b_score: float
    review: ReviewOutcome
    message: object
    agent_a_tool_calls: tuple[dict, ...]


def run_three_agent_pipeline(case: PatientCase, agent_a: AgentA, agent_b: AgentB,
                             agent_c: AgentC, attack: AttackSpec | None = None) -> ThreeAgentResult:
    """Execute A then B then C without allowing C to alter prior raw evidence."""
    output_a, message, calls = agent_a.run(case, attack_spec=attack)
    decision_b, score_b = agent_b.run(message, case)
    review = agent_c.run(decision_b, message, case)
    return ThreeAgentResult(output_a, decision_b, score_b, review, message, tuple(calls))
