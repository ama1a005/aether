"""Masked PPO baseline for query-budgeted heterogeneous causal search.

RL is a comparison method, not an AETHER novelty claim. The environment only
learns from executed evaluator results and shares the same candidate masks and
query definition used by deterministic search.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Callable, Sequence

import numpy as np
import torch
from torch import nn
from torch.distributions import Categorical

from discovery.budgeted import Candidate, Evaluation, QueryRecord, SearchConfig, SearchResult


@dataclass(frozen=True)
class RewardWeights:
    """Predeclared scalarization; every component remains separately observable."""

    effect: float = 1.0
    benign: float = 1.0
    size: float = 0.1
    cost: float = 0.001
    feasible_stop_bonus: float = 0.25

    def __post_init__(self) -> None:
        if any(not isfinite(value) or value < 0 for value in vars(self).values()):
            raise ValueError("Reward weights must be finite and nonnegative")


@dataclass(frozen=True)
class PPOConfig:
    """Deterministic PPO training and optimization configuration."""

    seed: int = 0
    training_steps: int = 512
    rollout_steps: int = 64
    update_epochs: int = 4
    hidden_size: int = 64
    learning_rate: float = 3e-4
    gamma: float = 0.99
    gae_lambda: float = 0.95
    clip_ratio: float = 0.2
    value_coefficient: float = 0.5
    entropy_coefficient: float = 0.01
    max_gradient_norm: float = 0.5

    def __post_init__(self) -> None:
        integers = (self.seed, self.training_steps, self.rollout_steps,
                    self.update_epochs, self.hidden_size)
        if any(type(value) is not int for value in integers) or self.seed < 0:
            raise ValueError("PPO integer configuration is invalid")
        if any(value < 1 for value in integers[1:]):
            raise ValueError("PPO counts must be positive")
        scalars = (self.learning_rate, self.gamma, self.gae_lambda, self.clip_ratio,
                   self.value_coefficient, self.entropy_coefficient, self.max_gradient_norm)
        if any(not isfinite(value) or value < 0 for value in scalars):
            raise ValueError("PPO scalar configuration must be finite and nonnegative")
        if not 0 < self.gamma <= 1 or not 0 <= self.gae_lambda <= 1 or self.clip_ratio <= 0:
            raise ValueError("PPO discount, GAE, or clipping range is invalid")


@dataclass(frozen=True)
class RewardBreakdown:
    """Auditable reward terms for one environment transition."""

    effect: float
    benign: float
    size: float
    cost: float
    feasible_stop: float
    total: float


@dataclass(frozen=True)
class PPOTraceRecord:
    """One sampled policy transition with its pre-action state and diagnostics."""

    step: int
    episode: int
    retained_before: tuple[str, ...]
    action: str
    action_mask: tuple[bool, ...]
    log_probability: float
    value_estimate: float
    reward: RewardBreakdown
    terminated: bool


@dataclass(frozen=True)
class PPOOutcome:
    """Search-compatible result plus the complete raw policy trajectory."""

    result: SearchResult
    training_trace: tuple[PPOTraceRecord, ...]


class CausalPruningEnv:
    """Typed node-pruning MDP backed exclusively by measured interventions."""

    def __init__(self, candidates: Sequence[Candidate], evaluator: Callable[[tuple[str, ...]], Evaluation],
                 search: SearchConfig, rewards: RewardWeights) -> None:
        self.candidates = tuple(sorted(candidates, key=lambda item: item.id))
        if not self.candidates or len({item.id for item in self.candidates}) != len(self.candidates):
            raise ValueError("RL candidates must be nonempty and unique")
        self.ids = tuple(item.id for item in self.candidates)
        self.evaluator = evaluator
        self.search = search
        self.rewards = rewards
        self.cache: dict[tuple[str, ...], Evaluation] = {}
        self.mask = self.ids
        self.current = self._query(self.mask)
        self.done = False

    @property
    def stop_action(self) -> int:
        """Return the fixed stop-action index."""
        return len(self.ids)

    def _query(self, mask: tuple[str, ...]) -> Evaluation:
        if mask not in self.cache:
            if len(self.cache) >= self.search.max_queries:
                raise RuntimeError("RL intervention-query budget exhausted")
            value = self.evaluator(mask)
            if not isinstance(value, Evaluation):
                raise TypeError("Evaluator must return Evaluation")
            self.cache[mask] = value
        return self.cache[mask]

    def reset(self) -> np.ndarray:
        """Start a new episode without erasing the global intervention ledger."""
        self.mask = self.ids
        self.current = self.cache[self.ids]
        self.done = False
        return self.observation()

    def feasible(self, evaluation: Evaluation) -> bool:
        """Apply the shared search feasibility constraints."""
        return (evaluation.faithfulness >= self.search.faithfulness_threshold
                and evaluation.benign_damage <= self.search.max_benign_damage)

    def observation(self) -> np.ndarray:
        """Return retained bits, region counts, metrics, and remaining budget."""
        retained = set(self.mask)
        bits = [float(item in retained) for item in self.ids]
        counts = [sum(item.id in retained and item.region == region for item in self.candidates)
                  / max(1, sum(item.region == region for item in self.candidates))
                  for region in ("sender", "message", "receiver")]
        budget = (self.search.max_queries - len(self.cache)) / self.search.max_queries
        return np.asarray(bits + counts + [self.current.faithfulness,
                          self.current.benign_damage, budget], dtype=np.float32)

    def action_mask(self) -> np.ndarray:
        """Mask removed nodes and unaffordable unseen interventions."""
        allowed = []
        for candidate_id in self.ids:
            child = tuple(item for item in self.mask if item != candidate_id)
            allowed.append(candidate_id in self.mask and
                           (child in self.cache or len(self.cache) < self.search.max_queries))
        return np.asarray([*allowed, True], dtype=np.bool_)

    def _utility(self, mask: tuple[str, ...], value: Evaluation) -> tuple[float, tuple[float, ...]]:
        terms = (self.rewards.effect * value.faithfulness,
                 -self.rewards.benign * value.benign_damage,
                 -self.rewards.size * len(mask) / len(self.ids),
                 -self.rewards.cost * value.forward_passes)
        return sum(terms), terms

    def step(self, action: int) -> tuple[np.ndarray, float, bool, RewardBreakdown]:
        """Apply one typed removal or stop action and expose all reward terms."""
        if self.done:
            raise RuntimeError("Episode already terminated")
        if type(action) is not int or action < 0 or action > self.stop_action:
            raise ValueError("Action index is invalid")
        if not self.action_mask()[action]:
            raise ValueError("Action is masked")
        previous_utility, _ = self._utility(self.mask, self.current)
        if action == self.stop_action:
            self.done = True
            bonus = self.rewards.feasible_stop_bonus if self.feasible(self.current) else 0.0
            breakdown = RewardBreakdown(0.0, 0.0, 0.0, 0.0, bonus, bonus)
            return self.observation(), bonus, True, breakdown
        child = tuple(item for item in self.mask if item != self.ids[action])
        evaluation = self._query(child)
        utility, terms = self._utility(child, evaluation)
        self.mask, self.current = child, evaluation
        self.done = not child or not self.action_mask()[:-1].any()
        delta = utility - previous_utility
        breakdown = RewardBreakdown(terms[0], terms[1], terms[2], terms[3], 0.0, delta)
        return self.observation(), delta, self.done, breakdown


class _ActorCritic(nn.Module):
    def __init__(self, observations: int, actions: int, hidden: int) -> None:
        super().__init__()
        self.shared = nn.Sequential(nn.Linear(observations, hidden), nn.Tanh(),
                                    nn.Linear(hidden, hidden), nn.Tanh())
        self.policy = nn.Linear(hidden, actions)
        self.value = nn.Linear(hidden, 1)

    def forward(self, states: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        encoded = self.shared(states)
        return self.policy(encoded), self.value(encoded).squeeze(-1)


def ppo_search(candidates: Sequence[Candidate], evaluator: Callable[[tuple[str, ...]], Evaluation],
               search_config: SearchConfig, ppo_config: PPOConfig = PPOConfig(),
               reward_weights: RewardWeights = RewardWeights()) -> SearchResult:
    """Train masked PPO and return the best actually measured feasible mask."""
    if search_config.split not in {"development", "synthetic"}:
        raise PermissionError("RL search is restricted to development or synthetic data")
    return ppo_search_with_trace(candidates, evaluator, search_config, ppo_config,
                                 reward_weights).result


def ppo_search_with_trace(candidates: Sequence[Candidate],
                          evaluator: Callable[[tuple[str, ...]], Evaluation],
                          search_config: SearchConfig, ppo_config: PPOConfig = PPOConfig(),
                          reward_weights: RewardWeights = RewardWeights()) -> PPOOutcome:
    """Train PPO and return both measured search output and raw policy transitions."""
    if search_config.split not in {"development", "synthetic"}:
        raise PermissionError("RL search is restricted to development or synthetic data")
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(ppo_config.seed)
        return _ppo_search(candidates, evaluator, search_config, ppo_config, reward_weights)


def _ppo_search(candidates: Sequence[Candidate], evaluator: Callable[[tuple[str, ...]], Evaluation],
                search_config: SearchConfig, ppo_config: PPOConfig,
                reward_weights: RewardWeights) -> PPOOutcome:
    env = CausalPruningEnv(candidates, evaluator, search_config, reward_weights)
    model = _ActorCritic(len(env.observation()), len(candidates) + 1, ppo_config.hidden_size)
    optimizer = torch.optim.Adam(model.parameters(), lr=ppo_config.learning_rate)
    transitions: list[tuple[np.ndarray, np.ndarray, int, float, float, bool, float]] = []
    trace: list[PPOTraceRecord] = []
    episode = 0
    state = env.reset()
    for step in range(ppo_config.training_steps):
        state_tensor = torch.from_numpy(state).unsqueeze(0)
        logits, value = model(state_tensor)
        allowed = env.action_mask()
        masked_logits = logits.masked_fill(~torch.from_numpy(allowed).unsqueeze(0), -torch.inf)
        distribution = Categorical(logits=masked_logits)
        action = distribution.sample()
        retained_before = env.mask
        next_state, reward, done, breakdown = env.step(int(action.item()))
        action_index = int(action.item())
        trace.append(PPOTraceRecord(step, episode, retained_before,
                    "stop" if action_index == env.stop_action else f"remove:{env.ids[action_index]}",
                    tuple(bool(item) for item in allowed), float(distribution.log_prob(action).item()),
                    float(value.item()), breakdown, done))
        transitions.append((state, allowed, int(action.item()), float(distribution.log_prob(action).item()),
                            float(value.item()), done, reward))
        if done:
            episode += 1
            state = env.reset()
        else:
            state = next_state
        if len(transitions) < ppo_config.rollout_steps:
            continue
        _update(model, optimizer, transitions, ppo_config)
        transitions.clear()
    if transitions:
        _update(model, optimizer, transitions, ppo_config)
    feasible = [mask for mask, value in env.cache.items() if env.feasible(value)]
    rank = lambda mask: (len(mask), -env.cache[mask].faithfulness,
                         env.cache[mask].benign_damage, mask)
    best = min(feasible or list(env.cache), key=rank)
    records = tuple(QueryRecord(mask, value) for mask, value in env.cache.items())
    result = SearchResult("ppo", best, env.cache[best], bool(feasible), "training_steps_complete",
                          None, len(records), sum(item.evaluation.forward_passes for item in records), records)
    return PPOOutcome(result, tuple(trace))


def _update(model: _ActorCritic, optimizer: torch.optim.Optimizer,
            transitions: list[tuple[np.ndarray, np.ndarray, int, float, float, bool, float]],
            config: PPOConfig) -> None:
    rewards = np.asarray([item[6] for item in transitions], dtype=np.float32)
    values = np.asarray([item[4] for item in transitions] + [0.0], dtype=np.float32)
    dones = np.asarray([item[5] for item in transitions], dtype=np.float32)
    advantages = np.zeros_like(rewards)
    estimate = 0.0
    for index in reversed(range(len(rewards))):
        delta = rewards[index] + config.gamma * values[index + 1] * (1 - dones[index]) - values[index]
        estimate = delta + config.gamma * config.gae_lambda * (1 - dones[index]) * estimate
        advantages[index] = estimate
    returns = advantages + values[:-1]
    advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
    states = torch.from_numpy(np.stack([item[0] for item in transitions]))
    masks = torch.from_numpy(np.stack([item[1] for item in transitions]))
    actions = torch.tensor([item[2] for item in transitions])
    old_log_probabilities = torch.tensor([item[3] for item in transitions])
    advantages_tensor = torch.from_numpy(advantages)
    returns_tensor = torch.from_numpy(returns)
    for _ in range(config.update_epochs):
        logits, predicted_values = model(states)
        distribution = Categorical(logits=logits.masked_fill(~masks, -torch.inf))
        log_probabilities = distribution.log_prob(actions)
        ratio = torch.exp(log_probabilities - old_log_probabilities)
        clipped = torch.clamp(ratio, 1 - config.clip_ratio, 1 + config.clip_ratio)
        policy_loss = -torch.min(ratio * advantages_tensor, clipped * advantages_tensor).mean()
        value_loss = torch.square(predicted_values - returns_tensor).mean()
        loss = (policy_loss + config.value_coefficient * value_loss
                - config.entropy_coefficient * distribution.entropy().mean())
        if not torch.isfinite(loss):
            raise RuntimeError("PPO optimization produced a non-finite loss")
        optimizer.zero_grad()
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), config.max_gradient_norm)
        optimizer.step()
