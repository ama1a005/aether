"""Published-compatible IOI logit-difference metrics."""

from __future__ import annotations

import torch


def logit_difference(
    logits: torch.Tensor, io_token_ids: torch.Tensor, subject_token_ids: torch.Tensor
) -> torch.Tensor:
    """Return per-example `logit(IO) - logit(subject)` at the answer position."""
    answer_logits = logits[:, -1, :]
    rows = torch.arange(answer_logits.shape[0], device=answer_logits.device)
    return answer_logits[rows, io_token_ids] - answer_logits[rows, subject_token_ids]


def normalized_recovery(clean: float, corrupted: float, patched: float) -> float:
    """Return `(patched-corrupted)/(clean-corrupted)` with explicit degeneracy rejection."""
    denominator = clean - corrupted
    if denominator == 0:
        raise ValueError("normalized recovery is undefined when clean equals corrupted")
    return (patched - corrupted) / denominator
