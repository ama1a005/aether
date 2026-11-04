"""Graph-aware hierarchical PPO for budgeted heterogeneous causal search.

The policy factorizes every action into operation, region, target and operator
components while a message-passing encoder consumes the explicit DCMG. This is
an AETHER search implementation; PPO itself remains prior art.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

import numpy as np
import torch
from torch import nn
from torch.distributions import Categorical

from discovery.budgeted import Candidate, Evaluation, QueryRecord, SearchConfig, SearchResult
from discovery.rl.ppo import PPOConfig, RewardBreakdown, RewardWeights

REGIONS = ("sender", "message", "receiver", "bridge", "none")
OPERATIONS = ("node_intervention", "edge_cut", "stop")


@dataclass(frozen=True)
class CausalEdge:
    """One explicitly addressable DCMG edge."""

    id: str
    source: str
    target: str
    kind: str = "causal"
    bridge: bool = False

    def __post_init__(self) -> None:
        if not self.id or not self.source or not self.target or not self.kind:
            raise ValueError("Edge identity, endpoints and kind are required")
        if self.source == self.target:
            raise ValueError("Self edges are not valid intervention targets")


@dataclass(frozen=True)
class GraphSearchState:
    """Immutable intervention state supplied to the executed evaluator."""

    active_nodes: tuple[str, ...]
    active_edges: tuple[str, ...]
    interventions: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class HierarchicalAction:
    """A typed operation/region/target/operator decision."""

    operation: str
    region: str
    target: str
    operator: str


@dataclass(frozen=True)
class GraphQueryRecord:
    """One unique graph/intervention state and its executed measurement."""

    state: GraphSearchState
    evaluation: Evaluation


@dataclass(frozen=True)
class GraphObservation:
    """Numerical graph, experiment ledger and current objective state."""

    node_features: np.ndarray
    adjacency: np.ndarray
    context: np.ndarray


@dataclass(frozen=True)
class HierarchicalTraceRecord:
    """One auditable factorized policy transition."""

    step: int
    episode: int
    state: GraphSearchState
    action: HierarchicalAction
    action_mask: tuple[bool, ...]
    reward: RewardBreakdown
    terminated: bool


@dataclass(frozen=True)
class HierarchicalOutcome:
    """Search-compatible output plus policy trajectory and action catalogue."""

    result: SearchResult
    training_trace: tuple[HierarchicalTraceRecord, ...]
    actions: tuple[HierarchicalAction, ...]
    selected_state: GraphSearchState
    graph_records: tuple[GraphQueryRecord, ...]
    repair_complete: bool


class HierarchicalCausalEnv:
    """Fully observed DCMG intervention environment with a global query ledger."""

    def __init__(self, candidates: Sequence[Candidate], edges: Sequence[CausalEdge],
                 evaluator: Callable[[GraphSearchState], Evaluation], search: SearchConfig,
                 rewards: RewardWeights, *, node_operators: Sequence[str] = ("prune",)) -> None:
        self.candidates = tuple(sorted(candidates, key=lambda item: item.id))
        self.edges = tuple(sorted(edges, key=lambda item: item.id))
        self.evaluator = evaluator
        self.search = search
        self.rewards = rewards
        self.node_operators = tuple(node_operators)
        self.ids = tuple(item.id for item in self.candidates)
        self.edge_ids = tuple(item.id for item in self.edges)
        if not self.candidates or len(set(self.ids)) != len(self.ids):
            raise ValueError("Graph candidates must be nonempty and unique")
        if (not self.node_operators
                or any(not isinstance(item, str) or not item for item in self.node_operators)):
            raise ValueError("At least one named node operator is required")
        if len(set(self.node_operators)) != len(self.node_operators):
            raise ValueError("Node operators must be unique")
        if set(self.node_operators) & {"cut", "stop"}:
            raise ValueError("Node operators cannot use reserved edge/stop names")
        if len(set(self.edge_ids)) != len(self.edge_ids):
            raise ValueError("Edge IDs must be unique")
        known = set(self.ids)
        if any(edge.source not in known or edge.target not in known for edge in self.edges):
            raise ValueError("Every edge endpoint must name a candidate")
        self.actions = self._build_actions()
        self.cache: dict[GraphSearchState, Evaluation] = {}
        self.query_limit = self.search.max_queries
        self.initial = GraphSearchState(self.ids, self.edge_ids)
        self.state = self.initial
        self.current = self._query(self.state)
        self.done = False

    def _build_actions(self) -> tuple[HierarchicalAction, ...]:
        actions = [HierarchicalAction("node_intervention", node.region, node.id, operator)
                   for node in self.candidates for operator in self.node_operators]
        by_id = {item.id: item for item in self.candidates}
        for edge in self.edges:
            region = "bridge" if edge.bridge or by_id[edge.source].region != by_id[edge.target].region \
                else by_id[edge.source].region
            actions.append(HierarchicalAction("edge_cut", region, edge.id, "cut"))
        actions.append(HierarchicalAction("stop", "none", "stop", "stop"))
        return tuple(actions)

    def _query(self, state: GraphSearchState) -> Evaluation:
        if state not in self.cache:
            if len(self.cache) >= self.search.max_queries:
                raise RuntimeError("Hierarchical RL intervention-query budget exhausted")
            value = self.evaluator(state)
            if not isinstance(value, Evaluation):
                raise TypeError("Evaluator must return Evaluation")
            self.cache[state] = value
        return self.cache[state]

    def reset(self) -> GraphObservation:
        """Reset graph state without erasing the global experiment ledger."""
        self.state = self.initial
        self.current = self.cache[self.initial]
        self.done = False
        return self.observation()

    def feasible(self, value: Evaluation) -> bool:
        """Apply shared causal-faithfulness and benign-damage constraints."""
        return (value.faithfulness >= self.search.faithfulness_threshold
                and value.benign_damage <= self.search.max_benign_damage)

    def action_mask(self) -> np.ndarray:
        """Mask repeated interventions, inactive targets and unaffordable queries."""
        active_nodes = set(self.state.active_nodes)
        active_edges = set(self.state.active_edges)
        used = {target for target, _ in self.state.interventions}
        allowed: list[bool] = []
        for action in self.actions:
            if action.operation == "stop":
                allowed.append(True)
                continue
            available = ((action.operation == "node_intervention" and action.target in active_nodes
                          and action.target not in used)
                         or (action.operation == "edge_cut" and action.target in active_edges))
            if not available:
                allowed.append(False)
                continue
            next_state = self.transition(action)
            allowed.append(next_state in self.cache or len(self.cache) < self.query_limit)
        return np.asarray(allowed, dtype=np.bool_)

    def transition(self, action: HierarchicalAction) -> GraphSearchState:
        """Return the deterministic graph state produced by a typed action."""
        nodes = set(self.state.active_nodes)
        edges = set(self.state.active_edges)
        interventions = dict(self.state.interventions)
        if action.operation == "node_intervention":
            interventions[action.target] = action.operator
            if action.operator == "prune":
                nodes.remove(action.target)
                edges = {edge.id for edge in self.edges if edge.id in edges
                         and edge.source in nodes and edge.target in nodes}
        elif action.operation == "edge_cut":
            edges.remove(action.target)
        else:
            raise ValueError("Stop has no successor graph state")
        return GraphSearchState(tuple(sorted(nodes)), tuple(sorted(edges)),
                                tuple(sorted(interventions.items())))

    def _utility(self, state: GraphSearchState, value: Evaluation) -> tuple[float, ...]:
        numerator = len(state.active_nodes) + len(state.active_edges)
        size = numerator / max(1, len(self.ids) + len(self.edge_ids))
        return (self.rewards.effect * value.faithfulness,
                -self.rewards.benign * value.benign_damage,
                -self.rewards.size * size,
                -self.rewards.cost * value.forward_passes)

    def step(self, action_index: int) -> tuple[GraphObservation, float, bool, RewardBreakdown]:
        """Execute one catalogue action and expose every reward component."""
        if self.done:
            raise RuntimeError("Episode already terminated")
        if type(action_index) is not int or not 0 <= action_index < len(self.actions):
            raise ValueError("Action index is invalid")
        if not self.action_mask()[action_index]:
            raise ValueError("Action is masked")
        action = self.actions[action_index]
        if action.operation == "stop":
            self.done = True
            bonus = self.rewards.feasible_stop_bonus if self.feasible(self.current) else 0.0
            breakdown = RewardBreakdown(0.0, 0.0, 0.0, 0.0, bonus, bonus)
            return self.observation(), bonus, True, breakdown
        previous = self._utility(self.state, self.current)
        successor = self.transition(action)
        cached = successor in self.cache
        value = self._query(successor)
        current = self._utility(successor, value)
        self.state, self.current = successor, value
        effect, benign, size = (current[index] - previous[index] for index in range(3))
        cost = 0.0 if cached else -self.rewards.cost * value.forward_passes
        total = effect + benign + size + cost
        self.done = not self.action_mask()[:-1].any()
        breakdown = RewardBreakdown(effect, benign, size, cost, 0.0, total)
        return self.observation(), total, self.done, breakdown

    def observation(self) -> GraphObservation:
        """Encode active topology, typed nodes, interventions and full query ledger."""
        active_nodes = set(self.state.active_nodes)
        active_edges = set(self.state.active_edges)
        interventions = dict(self.state.interventions)
        operators = self.node_operators
        node_features = []
        for node in self.candidates:
            incident = [edge for edge in self.edges if edge.source == node.id or edge.target == node.id]
            node_features.append([
                float(node.id in active_nodes),
                *(float(node.region == region) for region in REGIONS[:3]),
                sum(edge.source == node.id and edge.id in active_edges
                    for edge in self.edges) / max(1, len(self.ids)),
                sum(edge.target == node.id and edge.id in active_edges
                    for edge in self.edges) / max(1, len(self.ids)),
                float(any(edge.bridge for edge in incident)),
                *(float(interventions.get(node.id) == operator) for operator in operators),
            ])
        adjacency = np.zeros((len(self.ids), len(self.ids)), dtype=np.float32)
        indices = {node: index for index, node in enumerate(self.ids)}
        for edge in self.edges:
            if edge.id in active_edges:
                adjacency[indices[edge.source], indices[edge.target]] = 1.0
        current_bits = [float(node in active_nodes) for node in self.ids]
        current_edges = [float(edge in active_edges) for edge in self.edge_ids]
        action_bits = [float((action.target, action.operator) in self.state.interventions)
                       for action in self.actions[:-1]]
        ledger: list[float] = []
        for state, value in sorted(self.cache.items(), key=lambda item: repr(item[0])):
            state_interventions = set(state.interventions)
            ledger.extend(float(node in state.active_nodes) for node in self.ids)
            ledger.extend(float(edge in state.active_edges) for edge in self.edge_ids)
            ledger.extend(float((action.target, action.operator) in state_interventions)
                          for action in self.actions[:-1])
            ledger.extend((value.faithfulness, value.benign_damage,
                           float(value.forward_passes), 1.0))
        row_width = len(self.ids) + len(self.edge_ids) + len(self.actions) - 1 + 4
        ledger.extend([0.0] * ((self.search.max_queries - len(self.cache)) * row_width))
        context = [*current_bits, *current_edges, *action_bits,
                   self.current.faithfulness, self.current.benign_damage,
                   (self.search.max_queries - len(self.cache)) / self.search.max_queries,
                   *ledger]
        return GraphObservation(np.asarray(node_features, dtype=np.float32), adjacency,
                                np.asarray(context, dtype=np.float32))


class _GraphActorCritic(nn.Module):
    """Message-passing actor with factorized operation/region/target/operator logits."""

    def __init__(self, node_features: int, context_size: int, candidates: int,
                 edges: Sequence[CausalEdge], actions: Sequence[HierarchicalAction],
                 operators: Sequence[str], hidden: int) -> None:
        super().__init__()
        self.edges = tuple(edges)
        self.actions = tuple(actions)
        self.operator_names = tuple(operators) + ("cut", "stop")
        self.node_input = nn.Linear(node_features, hidden)
        self.message = nn.Linear(hidden, hidden)
        self.context = nn.Linear(context_size, hidden)
        self.joint = nn.Linear(hidden * 2, hidden)
        self.operation = nn.Linear(hidden, len(OPERATIONS))
        self.region = nn.Linear(hidden, len(REGIONS))
        self.operator = nn.Linear(hidden, len(self.operator_names))
        self.node_score = nn.Linear(hidden * 2, 1)
        self.edge_score = nn.Linear(hidden * 3 + 1, 1)
        self.stop_score = nn.Linear(hidden, 1)
        self.value = nn.Linear(hidden, 1)

    def forward(self, nodes: torch.Tensor, adjacency: torch.Tensor,
                context: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        h = torch.tanh(self.node_input(nodes))
        degrees = adjacency.sum(dim=-1, keepdim=True).clamp_min(1.0)
        h = torch.tanh(h + self.message(torch.bmm(adjacency, h) / degrees))
        pooled = h.mean(dim=1)
        encoded = torch.tanh(self.joint(torch.cat((pooled, torch.tanh(self.context(context))), dim=-1)))
        operation = self.operation(encoded)
        region = self.region(encoded)
        operator = self.operator(encoded)
        expanded = encoded.unsqueeze(1).expand(-1, h.shape[1], -1)
        node_logits = self.node_score(torch.cat((h, expanded), -1)).squeeze(-1)
        edge_logits = []
        node_ids = [action.target for action in self.actions
                    if action.operation == "node_intervention" and action.operator == self.operator_names[0]]
        node_index = {name: index for index, name in enumerate(node_ids)}
        for edge in self.edges:
            features = torch.cat((h[:, node_index[edge.source]], h[:, node_index[edge.target]], encoded,
                                  torch.full((h.shape[0], 1), float(edge.bridge), device=h.device)), -1)
            edge_logits.append(self.edge_score(features).squeeze(-1))
        edge_logits_tensor = torch.stack(edge_logits, 1) if edge_logits else h.new_zeros((h.shape[0], 0))
        action_logits = []
        for action in self.actions:
            base = operation[:, OPERATIONS.index(action.operation)] + region[:, REGIONS.index(action.region)]
            operator_index = self.operator_names.index(action.operator)
            base = base + operator[:, operator_index]
            if action.operation == "node_intervention":
                base = base + node_logits[:, node_index[action.target]]
            elif action.operation == "edge_cut":
                edge_index = next(index for index, edge in enumerate(self.edges)
                                  if edge.id == action.target)
                base = base + edge_logits_tensor[:, edge_index]
            else:
                base = base + self.stop_score(encoded).squeeze(-1)
            action_logits.append(base)
        return torch.stack(action_logits, 1), self.value(encoded).squeeze(-1)


def hierarchical_ppo_search(candidates: Sequence[Candidate], edges: Sequence[CausalEdge],
                            evaluator: Callable[[GraphSearchState], Evaluation],
                            search_config: SearchConfig, ppo_config: PPOConfig = PPOConfig(),
                            reward_weights: RewardWeights = RewardWeights(), *,
                            node_operators: Sequence[str] = ("prune",)) -> HierarchicalOutcome:
    """Train graph-aware factorized PPO and return measured synthetic/development search."""
    if search_config.split not in {"development", "synthetic"}:
        raise PermissionError("Hierarchical RL is restricted to development or synthetic data")
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(ppo_config.seed)
        env = HierarchicalCausalEnv(candidates, edges, evaluator, search_config,
                                    reward_weights, node_operators=node_operators)
        # Worst-case verification of successive single-node removals needs the
        # triangular number of node queries. The reserve remains inside the
        # method's declared global intervention budget.
        repair_reserve = min(len(candidates) * (len(candidates) + 1) // 2,
                             max(0, search_config.max_queries - 1))
        env.query_limit = search_config.max_queries - repair_reserve
        sample = env.observation()
        model = _GraphActorCritic(sample.node_features.shape[1], len(sample.context), len(candidates),
                                  env.edges, env.actions, env.node_operators, ppo_config.hidden_size)
        optimizer = torch.optim.Adam(model.parameters(), lr=ppo_config.learning_rate)
        transitions: list[tuple[GraphObservation, np.ndarray, int, float, float, bool, float]] = []
        trace: list[HierarchicalTraceRecord] = []
        state = env.reset()
        episode = 0
        for step in range(ppo_config.training_steps):
            logits, value = _forward_one(model, state)
            allowed = env.action_mask()
            distribution = Categorical(logits=logits.masked_fill(~torch.from_numpy(allowed), -torch.inf))
            action_tensor = distribution.sample()
            action = int(action_tensor.item())
            before = env.state
            next_state, reward, done, breakdown = env.step(action)
            transitions.append((state, allowed, action,
                                float(distribution.log_prob(action_tensor).detach().item()),
                                float(value.item()), done, reward))
            trace.append(HierarchicalTraceRecord(step, episode, before, env.actions[action],
                                                 tuple(bool(item) for item in allowed), breakdown, done))
            state = env.reset() if done else next_state
            if done:
                episode += 1
            if len(transitions) >= ppo_config.rollout_steps:
                _graph_update(model, optimizer, transitions, ppo_config,
                              0.0 if done else float(_forward_one(model, state)[1].item()))
                transitions.clear()
        if transitions:
            _graph_update(model, optimizer, transitions, ppo_config,
                          0.0 if transitions[-1][5] else float(_forward_one(model, state)[1].item()))
        env.query_limit = search_config.max_queries
        feasible = [(state, value) for state, value in env.cache.items() if env.feasible(value)]
        pool = feasible or list(env.cache.items())
        best_state, best_value = min(pool, key=lambda item: (
            len(item[0].active_nodes), len(item[0].active_edges), -item[1].faithfulness,
            item[1].benign_damage, repr(item[0])))
        # Deterministic one-step repair uses only the remaining shared query
        # budget. It establishes local node minimality without pretending that
        # the sampled policy itself visited the repaired state.
        improved = "prune" in env.node_operators
        repair_complete = False
        while improved and len(env.cache) < search_config.max_queries:
            improved = False
            tested_all = True
            children: list[tuple[GraphSearchState, Evaluation]] = []
            for action in env.actions:
                if (action.operation != "node_intervention" or action.operator != "prune"
                        or action.target not in best_state.active_nodes
                        or action.target in dict(best_state.interventions)):
                    continue
                env.state = best_state
                child = env.transition(action)
                if child not in env.cache and len(env.cache) >= search_config.max_queries:
                    tested_all = False
                    break
                value = env._query(child)
                if env.feasible(value) and len(child.active_nodes) < len(best_state.active_nodes):
                    children.append((child, value))
            if children:
                best_state, best_value = min(children, key=lambda item: (
                    len(item[0].active_nodes), len(item[0].active_edges),
                    -item[1].faithfulness, item[1].benign_damage, repr(item[0])))
                improved = True
            else:
                repair_complete = tested_all
        graph_records = tuple(GraphQueryRecord(state, value) for state, value in env.cache.items())
        records = tuple(QueryRecord(state.active_nodes, value) for state, value in env.cache.items())
        stop_reason = "locally_verified" if repair_complete else "repair_budget_exhausted"
        result = SearchResult("hierarchical_graph_ppo_repair", best_state.active_nodes, best_value,
                              bool(feasible), stop_reason, repair_complete, len(records),
                              sum(record.evaluation.forward_passes for record in records), records)
        return HierarchicalOutcome(result, tuple(trace), env.actions, best_state, graph_records,
                                   repair_complete)


def _forward_one(model: _GraphActorCritic,
                 observation: GraphObservation) -> tuple[torch.Tensor, torch.Tensor]:
    logits, value = model(torch.from_numpy(observation.node_features).unsqueeze(0),
                          torch.from_numpy(observation.adjacency).unsqueeze(0),
                          torch.from_numpy(observation.context).unsqueeze(0))
    return logits.squeeze(0), value.squeeze(0)


def _graph_update(model: _GraphActorCritic, optimizer: torch.optim.Optimizer,
                  transitions: list[tuple[GraphObservation, np.ndarray, int, float, float, bool, float]],
                  config: PPOConfig, bootstrap: float) -> None:
    rewards = np.asarray([item[6] for item in transitions], dtype=np.float32)
    values = np.asarray([item[4] for item in transitions] + [bootstrap], dtype=np.float32)
    dones = np.asarray([item[5] for item in transitions], dtype=np.float32)
    advantages = np.zeros_like(rewards)
    estimate = 0.0
    for index in reversed(range(len(rewards))):
        delta = rewards[index] + config.gamma * values[index + 1] * (1 - dones[index]) - values[index]
        estimate = delta + config.gamma * config.gae_lambda * (1 - dones[index]) * estimate
        advantages[index] = estimate
    returns = advantages + values[:-1]
    advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
    nodes = torch.from_numpy(np.stack([item[0].node_features for item in transitions]))
    adjacency = torch.from_numpy(np.stack([item[0].adjacency for item in transitions]))
    contexts = torch.from_numpy(np.stack([item[0].context for item in transitions]))
    masks = torch.from_numpy(np.stack([item[1] for item in transitions]))
    actions = torch.tensor([item[2] for item in transitions])
    old_logs = torch.tensor([item[3] for item in transitions])
    advantage_tensor = torch.from_numpy(advantages)
    return_tensor = torch.from_numpy(returns)
    for _ in range(config.update_epochs):
        logits, predicted = model(nodes, adjacency, contexts)
        distribution = Categorical(logits=logits.masked_fill(~masks, -torch.inf))
        ratios = torch.exp(distribution.log_prob(actions) - old_logs)
        clipped = torch.clamp(ratios, 1 - config.clip_ratio, 1 + config.clip_ratio)
        policy_loss = -torch.min(ratios * advantage_tensor, clipped * advantage_tensor).mean()
        value_loss = torch.square(predicted - return_tensor).mean()
        loss = (policy_loss + config.value_coefficient * value_loss
                - config.entropy_coefficient * distribution.entropy().mean())
        if not torch.isfinite(loss):
            raise RuntimeError("Hierarchical PPO produced a non-finite loss")
        optimizer.zero_grad()
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), config.max_gradient_norm, error_if_nonfinite=True)
        optimizer.step()
