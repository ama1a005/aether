"""Additive real-DCMG evidence records; frozen shared contracts remain unchanged."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

EvidenceStatus = Literal["candidate", "supported", "rejected", "insufficient"]


@dataclass(frozen=True)
class CausalEdgeEvidence:
    """Machine-readable evidence for one heterogeneous candidate edge."""

    edge_id: str
    source_node: str
    target_node: str
    source_type: str
    target_type: str
    evidence_type: str
    intervention_operator: str
    pair_ids: tuple[str, ...]
    n_attempted: int
    n_eligible: int
    effect_values: tuple[float, ...]
    summary_effect: float | None
    effect_direction: str
    control_effect: float | None
    artifact_refs: tuple[str, ...]
    manifest_refs: tuple[str, ...]
    split: str
    status: EvidenceStatus

    def __post_init__(self) -> None:
        if self.status == "supported" and "intervention" not in self.evidence_type:
            raise ValueError("supported edges require causal intervention evidence")
        if self.status == "supported" and (self.n_eligible == 0 or not self.effect_values):
            raise ValueError("supported edges require eligible intervention effects")
        if self.split != "development":
            raise PermissionError("candidate discovery is development-only")
        if self.n_eligible > self.n_attempted:
            raise ValueError("eligible count cannot exceed attempted count")

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-compatible evidence object."""
        return asdict(self)
