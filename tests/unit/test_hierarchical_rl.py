import numpy as np
import pytest

from discovery.budgeted import Candidate, Evaluation, SearchConfig
from discovery.rl.hierarchical import (CausalEdge, GraphSearchState, HierarchicalCausalEnv,
                                       hierarchical_ppo_search)
from discovery.rl.ppo import PPOConfig, RewardWeights


CANDIDATES = tuple(Candidate(identifier, region) for identifier, region in (
    ("S", "sender"), ("SN", "sender"), ("M", "message"),
    ("MN", "message"), ("R", "receiver"), ("RN", "receiver")))
EDGES = (
    CausalEdge("S_M", "S", "M", bridge=True),
    CausalEdge("M_R", "M", "R", bridge=True),
    CausalEdge("SN_MN", "SN", "MN", bridge=True),
    CausalEdge("MN_RN", "MN", "RN", bridge=True),
)


def evaluator(state: GraphSearchState) -> Evaluation:
    nodes = set(state.active_nodes)
    edges = set(state.active_edges)
    path = {"S", "M", "R"} <= nodes and {"S_M", "M_R"} <= edges
    return Evaluation(float(path), 0.0, 2,
                      {"active_nodes": list(state.active_nodes),
                       "active_edges": list(state.active_edges),
                       "interventions": list(state.interventions)})


def action_index(env, operation, target, operator):
    return next(index for index, action in enumerate(env.actions)
                if (action.operation, action.target, action.operator) ==
                (operation, target, operator))


def test_hierarchical_actions_encode_region_target_operator_and_edge_cut():
    env = HierarchicalCausalEnv(CANDIDATES, EDGES, evaluator,
                                SearchConfig(max_queries=12, split="synthetic"),
                                RewardWeights(), node_operators=("prune", "mean"))
    mean_m = action_index(env, "node_intervention", "M", "mean")
    cut = action_index(env, "edge_cut", "SN_MN", "cut")
    assert env.actions[mean_m].region == "message"
    assert env.actions[cut].region == "bridge"
    before = env.observation()
    env.step(cut)
    after = env.observation()
    assert after.adjacency.sum() == before.adjacency.sum() - 1
    assert "SN_MN" not in env.state.active_edges
    assert not env.action_mask()[cut]
    _, _, _, reward = env.step(mean_m)
    assert ("M", "mean") in env.state.interventions
    assert "M" in env.state.active_nodes
    assert reward.total == pytest.approx(sum((reward.effect, reward.benign, reward.size,
                                              reward.cost, reward.feasible_stop)))


def test_pruning_removes_incident_edges_and_observation_contains_graph_and_ledger():
    env = HierarchicalCausalEnv(CANDIDATES, EDGES, evaluator,
                                SearchConfig(max_queries=8, split="synthetic"),
                                RewardWeights())
    observation = env.observation()
    assert observation.node_features.shape[0] == len(CANDIDATES)
    assert observation.adjacency.shape == (len(CANDIDATES), len(CANDIDATES))
    prune = action_index(env, "node_intervention", "SN", "prune")
    env.step(prune)
    assert "SN" not in env.state.active_nodes
    assert not ({"SN_MN"} & set(env.state.active_edges))
    env.reset()
    _, _, _, cached = env.step(prune)
    assert cached.cost == 0
    assert len(env.cache) == 2


def test_graph_validation_and_budget_fail_closed():
    with pytest.raises(ValueError, match="endpoint"):
        HierarchicalCausalEnv(CANDIDATES, [CausalEdge("bad", "S", "missing")], evaluator,
                              SearchConfig(split="synthetic"), RewardWeights())
    env = HierarchicalCausalEnv(CANDIDATES, EDGES, evaluator,
                                SearchConfig(max_queries=1, split="synthetic"), RewardWeights())
    assert not env.action_mask()[:-1].any()
    assert env.action_mask()[-1]


def test_graph_ppo_is_seeded_budgeted_and_recovers_branching_path():
    search = SearchConfig(max_queries=64, faithfulness_threshold=.99,
                          max_benign_damage=0, split="synthetic")
    config = PPOConfig(seed=9, training_steps=256, rollout_steps=32,
                       update_epochs=2, hidden_size=32)
    first = hierarchical_ppo_search(CANDIDATES, EDGES, evaluator, search, config)
    second = hierarchical_ppo_search(CANDIDATES, EDGES, evaluator, search, config)
    assert first.result.retained == second.result.retained == ("M", "R", "S")
    assert first.result.feasible
    assert first.repair_complete and first.result.one_step_locally_minimal
    assert first.result.method == "hierarchical_graph_ppo_repair"
    assert first.result.queries == second.result.queries <= search.max_queries
    assert len(first.training_trace) == config.training_steps
    assert {record.action.operation for record in first.training_trace} <= {
        "node_intervention", "edge_cut", "stop"}
    assert any(record.action.region == "bridge" for record in first.training_trace)
    assert all(np.isfinite(record.reward.total) for record in first.training_trace)
