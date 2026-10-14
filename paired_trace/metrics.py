"""Outcome, mediation-recovery, and token-alignment rules."""

from __future__ import annotations

import torch

LABEL_TO_DECISION = {"A": "ESCALATE", "B": "DO_NOT_ESCALATE"}


def validate_label_tokens(tokenizer: object) -> dict[str, int]:
    """Require the predeclared A/B outcome labels to be single tokens."""
    labels: dict[str, int] = {}
    for label in LABEL_TO_DECISION:
        ids = tokenizer.encode(label, add_special_tokens=False)
        if len(ids) != 1:
            raise ValueError(f"outcome label {label!r} is not a single token")
        labels[label] = ids[0]
    if labels["A"] == labels["B"]:
        raise ValueError("outcome labels map to the same token")
    return labels


def escalation_margin(logits: torch.Tensor, label_ids: dict[str, int]) -> torch.Tensor:
    """Return `logit(A=ESCALATE) - logit(B=DO_NOT_ESCALATE)` at decision position."""
    final = logits[:, -1, :]
    return final[:, label_ids["A"]] - final[:, label_ids["B"]]


def mediation_recovery(clean: float, attacked: float, intervention: float, minimum: float = 1e-6) -> float:
    """Return unclipped `(intervention-attacked)/(clean-attacked)` or reject degeneracy."""
    denominator = clean - attacked
    if abs(denominator) < minimum:
        raise ValueError("clean/attacked score denominator is too small")
    return (intervention - attacked) / denominator


def validate_token_alignment(clean_ids: list[int], attacked_ids: list[int], position: int = -1) -> int:
    """Allow patching only equal-length inputs at a shared structural decision position."""
    if len(clean_ids) != len(attacked_ids):
        raise ValueError("paired token lengths differ")
    resolved = position if position >= 0 else len(clean_ids) + position
    if resolved < 0 or resolved >= len(clean_ids):
        raise ValueError("patch position is outside the token sequence")
    return resolved
