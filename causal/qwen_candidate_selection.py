"""Prospectively frozen DCAP discovery-only candidate selection for QCI-1."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
from statistics import median
from typing import Any, Iterable

import torch


@dataclass(frozen=True)
class CandidateScore:
    """One deterministic discovery-only candidate score."""

    candidate_id: str
    agent: str
    family: str
    a_to_b_median: float
    b_to_a_median: float
    aggregate_score: float
    case_count: int


def _vectors(payload: dict[str, torch.Tensor]) -> Iterable[tuple[str, str, torch.Tensor]]:
    """Yield frozen module and individual-head vectors from one DCAP artifact."""
    for key in sorted(payload):
        tensor = payload[key].float()
        if key.startswith("module."):
            yield key, "module", tensor.reshape(-1)
        elif key.startswith("head."):
            if tensor.ndim != 3 or tensor.shape[0] != 1 or tensor.shape[1] != 12:
                raise ValueError(f"unexpected pre-o_proj head tensor shape for {key}: {tuple(tensor.shape)}")
            prefix = key.removesuffix(".pre_o_proj_heads")
            for head in range(12):
                yield f"{prefix}.H{head}.pre_o_proj", "head", tensor[0, head].reshape(-1)
        else:
            raise ValueError(f"unexpected DCAP component key: {key}")


def _paired_scores(
    clean: dict[str, torch.Tensor], attacked: dict[str, torch.Tensor]
) -> dict[tuple[str, str], float]:
    """Return the exact frozen contrast score for every expanded candidate."""
    clean_vectors = {(identifier, family): vector for identifier, family, vector in _vectors(clean)}
    attacked_vectors = {(identifier, family): vector for identifier, family, vector in _vectors(attacked)}
    if clean_vectors.keys() != attacked_vectors.keys():
        raise ValueError("clean and attacked candidate sets differ")
    scores: dict[tuple[str, str], float] = {}
    for key, left in clean_vectors.items():
        right = attacked_vectors[key]
        denominator = 0.5 * (torch.linalg.vector_norm(left) + torch.linalg.vector_norm(right)) + 1e-8
        normalized_l2 = float(torch.linalg.vector_norm(left - right) / denominator)
        cosine = float(torch.nn.functional.cosine_similarity(left[None], right[None])[0])
        value = 0.5 * normalized_l2 + 0.5 * (1.0 - cosine)
        if not math.isfinite(value):
            raise ValueError(f"non-finite candidate score: {key[0]}")
        scores[key] = value
    return scores


def select_candidates(
    activation_root: Path, qualification_rows: list[dict[str, Any]], protocol: dict[str, Any]
) -> dict[str, Any]:
    """Select candidates using only prospectively listed discovery artifacts."""
    discovery_ids = tuple(protocol["discovery_case_ids"])
    audit_ids = set(protocol["development_audit_case_ids"])
    if set(discovery_ids) & audit_ids:
        raise ValueError("discovery and development-audit case IDs overlap")
    rows = {str(row["case_id"]): row for row in qualification_rows}
    if set(discovery_ids) - rows.keys():
        raise ValueError("qualification rows are missing discovery cases")
    values: dict[tuple[str, str, str], dict[str, list[float]]] = {}
    for case_id in discovery_ids:
        direction = str(rows[case_id]["direction"])
        if direction not in {"A_TO_B", "B_TO_A"}:
            raise ValueError(f"invalid attack direction: {direction}")
        for agent in protocol["selection"]["agents"]:
            clean_path = activation_root / f"{case_id}_{agent}_clean.pt"
            attacked_path = activation_root / f"{case_id}_{agent}_attacked.pt"
            if not clean_path.is_file() or not attacked_path.is_file():
                raise FileNotFoundError(f"missing discovery activation pair for {case_id}/{agent}")
            clean = torch.load(clean_path, map_location="cpu", weights_only=True)
            attacked = torch.load(attacked_path, map_location="cpu", weights_only=True)
            for (candidate_id, family), score in _paired_scores(clean, attacked).items():
                values.setdefault((agent, family, candidate_id), {"A_TO_B": [], "B_TO_A": []})[
                    direction
                ].append(score)
    scored: list[CandidateScore] = []
    for (agent, family, candidate_id), directions in values.items():
        if not directions["A_TO_B"] or not directions["B_TO_A"]:
            raise ValueError(f"candidate lacks both attack directions: {candidate_id}")
        left, right = median(directions["A_TO_B"]), median(directions["B_TO_A"])
        scored.append(CandidateScore(candidate_id, agent, family, left, right, min(left, right),
                                     len(directions["A_TO_B"]) + len(directions["B_TO_A"])))
    selected: list[CandidateScore] = []
    limits = {
        "module": int(protocol["selection"]["top_k_modules_per_agent"]),
        "head": int(protocol["selection"]["top_k_heads_per_agent"]),
    }
    for agent in protocol["selection"]["agents"]:
        for family, limit in limits.items():
            eligible = [item for item in scored if item.agent == agent and item.family == family]
            eligible.sort(key=lambda item: (-item.aggregate_score, item.candidate_id))
            selected.extend(eligible[:limit])
    selected.sort(key=lambda item: (item.agent, item.family, item.candidate_id))
    return {
        "protocol_version": protocol["protocol_version"],
        "source_partition": "discovery_only",
        "discovery_case_ids": list(discovery_ids),
        "development_audit_accessed": False,
        "candidate_universe_count": len(scored),
        "selected_count": len(selected),
        "selected": [asdict(item) for item in selected],
    }


def load_protocol(path: Path) -> dict[str, Any]:
    """Load and minimally validate the frozen QCI protocol."""
    protocol = json.loads(path.read_text(encoding="utf-8"))
    if protocol.get("status") != "prospectively_frozen_before_dcap_magnitude_ranking":
        raise ValueError("QCI protocol is not prospectively frozen")
    if protocol["selection"].get("audit_access_during_selection") is not False:
        raise ValueError("QCI selection must prohibit development-audit access")
    return protocol
