# AETHER Phase 1 RL Search Specification

## Status and claim boundary

PPO search is a mandatory Phase 1 comparison baseline. RL circuit discovery is
prior art and is not an AETHER novelty claim. AETHER's testable distinction is
the explicit heterogeneous intervention space spanning sender internals, the
serialized mediator, and receiver internals under one auditable query budget.

## Environment state and policy observation

The full environment state includes the global query cache. The feed-forward
policy receives the observation below and a valid-action mask; it does not see
the full cache. Thus this is a partially observed search policy, not a claim
that this observation is a sufficient Markov state. Policy generalization still
requires separate evaluation.

An instance contains a fixed ordered candidate set
`V = V_sender ∪ V_message ∪ V_receiver`. A state contains:

- one retained/not-retained bit per candidate;
- retained fractions for sender, message, and receiver regions;
- the measured faithfulness and benign damage of the current mask;
- remaining intervention-query fraction.

The discrete action set contains one remove action per typed candidate plus one
stop action. Removed candidates are masked. An unseen removal is also masked
when the global query budget is exhausted. Stop always remains available.

An episode begins at the complete candidate mask. Removing a candidate executes
or retrieves the exact resulting intervention mask. Stop terminates without an
intervention. Empty masks and states with no affordable removal terminate. The
global evaluator cache persists across episodes, so one unique mask corresponds
to at most one intervention query in a run.

## Reward

For measured mask `C`, define the auditable utility

```text
U(C) = lambda_effect * faithfulness(C)
     - lambda_benign * benign_damage(C)
     - lambda_size * |C| / |V|
```

A removal receives `U(C_next) - U(C_current) - lambda_cost * new_forward_passes`.
Cache hits incur zero additional forward cost. Recorded components are signed
transition contributions whose sum equals the reward. This corrects the earlier
constant-cost cancellation bug; historical runs are unchanged. A feasible stop receives the
predeclared stop bonus. Every term and every raw evaluator output is retained;
the scalar reward is an optimization signal, never a scientific endpoint.
Reward weights are frozen in the run configuration. Required ablations remove
the size, cost, and feasible-stop terms separately.

## PPO algorithm

The baseline uses a shared two-layer tanh actor-critic and masked categorical
policy. It applies generalized advantage estimation, the clipped PPO surrogate,
value regression, entropy regularization, gradient-norm clipping, deterministic
seeding, and non-finite-loss rejection. No third-party RL framework or hidden
fallback is used.

## Budget and comparison protocol

Random, greedy, beam, receiver-only search, and PPO must receive the same:

- ordered candidate set and granularity;
- evaluator and intervention semantics;
- development cases and seed policy;
- feasibility thresholds;
- unique-mask query definition and maximum query count.

Training compute, unique queries, forward passes, retained size, faithfulness,
benign damage, feasibility, and raw queries are reported separately. Cached
policy optimization does not create new causal evidence. Validation and test
remain locked until their separate approval gates are satisfied.

## Evidence levels

### Saved policies and inference

`ppo_search_with_trace` also returns a portable policy checkpoint. Use
`discovery.rl.policy.save_policy` and `load_policy` for validated JSON weights;
candidate identities/regions, architecture/training configuration and reward
weights are embedded. The run manifest hashes the checkpoint. Loading rejects
nonfinite weights, wrong parameter shapes and unsupported schemas.

`evaluate_policy` performs deterministic masked argmax inference without an
optimizer, on a fresh query ledger. It reports the terminal policy choice even
if that choice is infeasible. Candidate identities and regions must match the
trained policy; this architecture does not support arbitrary unseen graph sizes.
Its output is separate from the best-visited training search result. The smoke
runner evaluates the same synthetic task, so this is serialization/inference
acceptance, not evidence of out-of-distribution generalization. Development and
synthetic splits remain the only enabled splits.

The synthetic acceptance demonstrates software mechanics and known-path search
only. It does not demonstrate superiority, real-model stability, or causal
localization on AETHER data. Those require a qualified model, frozen candidate
graph, development comparison, reward ablations, and finally untouched held-out
confirmation under the repository's existing gates.
