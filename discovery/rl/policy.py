"""Portable JSON PPO checkpoints and isolated, frozen-policy evaluation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Sequence

import torch

from discovery.budgeted import Candidate, Evaluation, QueryRecord, SearchConfig, SearchResult
from discovery.rl.ppo import CausalPruningEnv, PPOConfig, RewardWeights, _ActorCritic


def _restore(checkpoint: dict[str, object]) -> tuple[_ActorCritic, tuple[Candidate, ...], RewardWeights]:
    if checkpoint.get("schema_version") != 1:
        raise ValueError("Unsupported PPO checkpoint schema")
    candidates = tuple(Candidate(**item) for item in checkpoint["candidates"])
    if not candidates or tuple(sorted(candidates, key=lambda item: item.id)) != candidates:
        raise ValueError("Checkpoint candidates must be nonempty and sorted")
    if len({item.id for item in candidates}) != len(candidates):
        raise ValueError("Duplicate checkpoint candidate IDs")
    config = PPOConfig(**checkpoint["training_config"])
    rewards = RewardWeights(**checkpoint["reward_weights"])
    with torch.random.fork_rng(devices=[]):
        model = _ActorCritic(len(candidates) + 6, len(candidates) + 1, config.hidden_size)
    state = {key: torch.tensor(value, dtype=torch.float32)
             for key, value in checkpoint["state_dict"].items()}
    if any(not torch.isfinite(value).all() for value in state.values()):
        raise ValueError("Checkpoint contains nonfinite parameters")
    model.load_state_dict(state, strict=True)
    model.eval()
    model.requires_grad_(False)
    return model, candidates, rewards


def save_policy(checkpoint: dict[str, object], path: str | Path) -> None:
    """Validate and save weights as JSON without executable pickle payloads."""
    _restore(checkpoint)
    Path(path).write_text(json.dumps(checkpoint, allow_nan=False), encoding="utf-8")


def load_policy(path: str | Path) -> dict[str, object]:
    """Load a checkpoint and reject invalid schema, dimensions, or weights."""
    checkpoint = json.loads(Path(path).read_text(encoding="utf-8"))
    _restore(checkpoint)
    return checkpoint


def evaluate_policy(checkpoint: dict[str, object], candidates: Sequence[Candidate],
                    evaluator: Callable[[tuple[str, ...]], Evaluation],
                    config: SearchConfig) -> SearchResult:
    """Evaluate greedy policy actions with a fresh query cache and no training.

    The returned mask is the terminal policy choice, even when infeasible;
    it is never replaced with the best training or evaluation mask.
    Held-out split access remains locked pending research qualification.
    """
    if config.split not in {"development", "synthetic"}:
        raise PermissionError("Frozen-policy evaluation requires development or synthetic data")
    model, expected, rewards = _restore(checkpoint)
    if tuple(sorted(candidates, key=lambda item: item.id)) != expected:
        raise ValueError("Policy candidate identities and regions do not match")
    env = CausalPruningEnv(expected, evaluator, config, rewards)
    with torch.no_grad():
        while not env.done:
            logits, _ = model(torch.from_numpy(env.observation()).unsqueeze(0))
            if not torch.isfinite(logits).all():
                raise RuntimeError("Policy produced nonfinite action logits")
            logits = logits.squeeze(0).masked_fill(~torch.from_numpy(env.action_mask()), -torch.inf)
            env.step(int(logits.argmax().item()))
    records = tuple(QueryRecord(mask, value) for mask, value in env.cache.items())
    return SearchResult("ppo_frozen_policy", env.mask, env.current, env.feasible(env.current),
                        "policy_terminated", None, len(records),
                        sum(item.evaluation.forward_passes for item in records), records)
