"""Bridge Verification Protocol evidence states."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Literal


class EvidenceLevel(IntEnum):
    """Maximum supported bridge evidence, never inferred from association alone."""

    ASSOCIATION = 0
    MEDIATOR_CAUSAL = 1
    SENDER_TO_MEDIATOR = 2
    RECEIVER_TO_OUTCOME = 3


@dataclass(frozen=True)
class BVPEvidence:
    """One explicit accepted/rejected/insufficient intervention record."""

    edge_id: str
    level: EvidenceLevel
    status: Literal["accepted", "rejected", "insufficient"]
    intervention_type: str
    pair_ids: tuple[str, ...]
    raw_effect: float | None
    normalized_recovery: float | None
    artifact_reference: str
    result_type: Literal["real_model", "synthetic", "calibration"]


def maximum_verified_level(records: list[BVPEvidence]) -> EvidenceLevel:
    """Return the highest accepted evidence level; rejected evidence never promotes."""
    accepted = [record.level for record in records if record.status == "accepted"]
    return max(accepted, default=EvidenceLevel.ASSOCIATION)
