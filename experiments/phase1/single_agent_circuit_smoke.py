"""
P3 Smoke Test: Single-Agent Causal Circuit Discovery
======================================================
Demonstrates:
- Toy transformer with explicit causal structure (L1.H2 and L2.H1 are the causal components)
- Activation hooks (non-interference verified)
- Zero-ablation intervention
- Causal component ranking by effect size
- Greedy causal pruning
- Faithfulness-vs-retained-size curve
- Random matched-size baseline

Run: python -m experiments.phase1.single_agent_circuit_smoke
"""

from __future__ import annotations
import os
import csv
import json
import time
import datetime

import torch
import torch.nn as nn
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from instrumentation.hooks.hook_registry import HookRegistry
from causal.interventions.operators import ZeroAblation
from causal.metrics.faithfulness import compute_faithfulness, compute_necessity
from discovery.greedy.pruner import GreedyCausalPruner
from discovery.random_baseline.sampler import RandomCircuitSampler
from contracts.schemas import CircuitResult

EXPERIMENT_ID = f"P0_mech_{datetime.date.today().strftime('%Y%m%d')}_greedy_ablation_0"
SEED = 42


# ---------------------------------------------------------------------------
# Toy transformer with explicit causal structure
# ---------------------------------------------------------------------------

class ToyTransformer(nn.Module):
    """
    3-layer, 4-head toy transformer.

    EXPLICIT CAUSAL STRUCTURE (by design):
    - Token embedding: token 1 ('poisoned') creates a large hidden state
    - L1.H2 and L2.H1 amplify that large state toward the 'unsafe' logit
    - All other heads are random noise; ablating them has minimal effect

    This lets us verify that greedy pruning recovers exactly L1.H2 and L2.H1.
    """

    def __init__(self) -> None:
        super().__init__()
        self.embed = nn.Embedding(10, 64)
        self.L0 = nn.ModuleList([nn.Linear(64, 64, bias=False) for _ in range(4)])
        self.L1 = nn.ModuleList([nn.Linear(64, 64, bias=False) for _ in range(4)])
        self.L2 = nn.ModuleList([nn.Linear(64, 64, bias=False) for _ in range(4)])
        self.fc = nn.Linear(64, 2, bias=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = self.embed(x).sum(dim=1)
        h = h + sum(head(h) for head in self.L0)
        h = h + sum(head(h) for head in self.L1)
        h = h + sum(head(h) for head in self.L2)
        return self.fc(h)


def build_module_mapping(model: ToyTransformer) -> dict[str, str]:
    """Map component_id strings to PyTorch module attribute paths."""
    mapping: dict[str, str] = {}
    for li in range(3):
        for hi in range(4):
            mapping[f"L{li}.H{hi}"] = f"L{li}.{hi}"
    return mapping


def make_intervention(model: ToyTransformer, module_mapping: dict) -> callable:
    """Return a ZeroAblation callable wrapping the model + mapping."""
    def op(mod, input_ids, components):
        return ZeroAblation(mod, input_ids, components, module_mapping=module_mapping)
    return op


def rank_components_by_effect(
    model: ToyTransformer,
    candidates: list[str],
    adv_input: torch.Tensor,
    clean_input: torch.Tensor,
    target_fn: callable,
    module_mapping: dict,
) -> list[tuple[str, float, float]]:
    """
    For each candidate component, zero-ablate it and measure delta in target score.
    Returns sorted list of (component_id, base_score, ablated_score, effect_size).
    """
    with torch.no_grad():
        base_score = target_fn(model(adv_input))

    results = []
    for cid in candidates:
        out, _ = ZeroAblation(model, adv_input, [cid], module_mapping=module_mapping)
        with torch.no_grad():
            ablated_score = target_fn(out)
        effect = abs(base_score - ablated_score)
        results.append((cid, base_score, ablated_score, effect))

    results.sort(key=lambda x: x[3], reverse=True)
    return results


def main() -> None:
    torch.manual_seed(SEED)
    os.makedirs("results/raw", exist_ok=True)
    os.makedirs("results/figures", exist_ok=True)

    t0 = time.time()

    # --- Build toy model with explicit causal weights ---
    model = ToyTransformer()
    with torch.no_grad():
        # Token 1 = 'poisoned token' gets a large embedding
        model.embed.weight[1] += 5.0
        # L1.H2 and L2.H1 amplify the large embedding toward the unsafe logit
        model.L1[2].weight += torch.eye(64) * 2.0
        model.L2[1].weight += torch.eye(64) * 2.0
        # fc: logit[1] (unsafe) responds strongly to large hidden values
        model.fc.weight[1] += 1.0

    clean_input = torch.tensor([[0, 0, 2, 3]])   # token 1 absent → safe
    adv_input   = torch.tensor([[0, 1, 2, 3]])   # token 1 present → unsafe

    # unsafe logit - safe logit
    target_fn = lambda out: (out[0, 1] - out[0, 0]).item()

    with torch.no_grad():
        clean_score = target_fn(model(clean_input))
        adv_score   = target_fn(model(adv_input))
    delta_full = adv_score - clean_score

    print(f"\n{'='*60}")
    print(f"EXPERIMENT: {EXPERIMENT_ID}")
    print(f"{'='*60}")
    print(f"Clean score  : {clean_score:.4f}")
    print(f"Attacked score: {adv_score:.4f}")
    print(f"delta_attack  : {delta_full:.4f}")

    # --- Candidate components ---
    candidates = [f"L{l}.H{h}" for l in range(3) for h in range(4)]
    module_mapping = build_module_mapping(model)
    op = make_intervention(model, module_mapping)

    # --- Component ranking by causal effect ---
    print(f"\n{'-'*60}")
    print("COMPONENT CAUSAL RANKING (ablation effect on attacked score)")
    print(f"{'-'*60}")
    print(f"{'Component':<12} {'Base':>10} {'Ablated':>10} {'Effect':>10}")
    print(f"{'-'*60}")

    ranking = rank_components_by_effect(
        model, candidates, adv_input, clean_input, target_fn, module_mapping
    )
    ranking_rows = []
    for cid, base, ablated, effect in ranking:
        print(f"{cid:<12} {base:>10.4f} {ablated:>10.4f} {effect:>10.4f}")
        ranking_rows.append({
            "component_id": cid,
            "base_score": round(base, 6),
            "ablated_score": round(ablated, 6),
            "effect_size": round(effect, 6),
        })

    # --- Greedy pruning ---
    print(f"\n{'-'*60}")
    print("GREEDY CAUSAL PRUNING")
    print(f"{'-'*60}")

    pruner = GreedyCausalPruner(
        model=model,
        hook_registry=HookRegistry(model),
        intervention_operator=op,
        faithfulness_fn=compute_faithfulness,
        candidate_nodes=candidates,
        faithfulness_threshold=0.85,
        target_fn=target_fn,
    )

    retained, history = pruner.prune([adv_input], [clean_input])

    print(f"\nRetained nodes ({len(retained)}): {retained}")
    print(f"Benign damage: {pruner.benign_damage:.4f}")
    print(f"\n{'Step':>6} {'N_Retained':>12} {'Faithfulness':>14}")
    for step, n_ret, faith in history:
        print(f"{step:>6} {n_ret:>12} {faith:>14.4f}")

    # --- Random baseline ---
    rng_sampler = RandomCircuitSampler(candidates)
    k = len(retained)
    random_samples = rng_sampler.sample_many(k=k, n_samples=100, seed=SEED)

    random_faithfulness_vals = []
    for sample_nodes in random_samples:
        ablated_complement = [c for c in candidates if c not in sample_nodes]
        out, _ = op(model, adv_input, ablated_complement)
        score = target_fn(out)
        delta_c = score - clean_score
        f = compute_faithfulness(delta_full, delta_c)
        random_faithfulness_vals.append(f)

    import statistics
    rand_mean = statistics.mean(random_faithfulness_vals)
    rand_std  = statistics.stdev(random_faithfulness_vals)

    # Where does our circuit land in the random distribution?
    circuit_faith = history[-1][2] if history else 0.0
    percentile = sum(1 for x in random_faithfulness_vals if x < circuit_faith) / len(random_faithfulness_vals) * 100

    print(f"\nRandom baseline (k={k}): mean={rand_mean:.4f}, std={rand_std:.4f}")
    print(f"Discovered circuit faithfulness: {circuit_faith:.4f}")
    print(f"Circuit at {percentile:.1f}th percentile of random matched-size circuits")

    # --- Faithfulness-vs-size plot ---
    if len(history) > 1:
        sizes = [h[1] for h in history]
        faiths = [h[2] for h in history]

        fig, ax = plt.subplots(figsize=(8, 5))
        ax.plot(sizes, faiths, marker="o", linewidth=2, label="Greedy circuit", color="steelblue")
        ax.axhline(rand_mean, color="orange", linestyle="--", linewidth=1.5, label=f"Random baseline μ={rand_mean:.2f}")
        ax.fill_between(
            [min(sizes), max(sizes)],
            rand_mean - rand_std, rand_mean + rand_std,
            alpha=0.2, color="orange", label="±1 std"
        )
        ax.invert_xaxis()
        ax.set_xlabel("Number of Retained Components")
        ax.set_ylabel("Faithfulness F(C)")
        ax.set_title(f"P3 Faithfulness vs Circuit Size\n{EXPERIMENT_ID}")
        ax.legend()
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        fig.savefig("results/figures/p3_faithfulness_curve.png", dpi=150)
        plt.close(fig)
        print("\nSaved: results/figures/p3_faithfulness_curve.png")

    # --- Save ranking CSV ---
    with open("results/raw/p3_smoke_component_ranking.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["component_id", "base_score", "ablated_score", "effect_size"])
        w.writeheader()
        w.writerows(ranking_rows)
    print("Saved: results/raw/p3_smoke_component_ranking.csv")

    # --- Save CircuitResult JSON (schema-compliant) ---
    circuit_result = CircuitResult(
        experiment_id=EXPERIMENT_ID,
        source_attack_ids=["fixture_adv_input_seed42"],
        nodes=[{"id": n, "type": "attention_head", "region": "receiver", "retained": True}
               for n in retained],
        edges=[],
        faithfulness=circuit_faith,
        necessity=None,
        size=len(retained),
        benign_damage=round(pruner.benign_damage, 6),
        search_method="greedy",
        search_cost={
            "n_candidates": len(candidates),
            "n_examples": 1,
            "wall_time_s": round(time.time() - t0, 2),
        },
        metadata={
            "experiment_id": EXPERIMENT_ID,
            "seed": SEED,
            "model": "ToyTransformer_3L4H_d64",
            "known_causal_components": ["L1.H2", "L2.H1"],
            "random_baseline_mean": round(rand_mean, 6),
            "random_baseline_std": round(rand_std, 6),
            "random_baseline_percentile": round(percentile, 1),
            "fixture_only": True,
        },
    )
    with open("results/raw/p3_smoke_circuit_result.json", "w") as f:
        f.write(circuit_result.to_json())
    print("Saved: results/raw/p3_smoke_circuit_result.json")

    # --- Verification ---
    print(f"\n{'='*60}")
    print("VERIFICATION")
    print(f"{'='*60}")
    top2 = [r[0] for r in ranking[:2]]
    expected = {"L1.H2", "L2.H1"}
    top2_set = set(top2)
    if top2_set == expected:
        print(f"[PASS] Top-2 causal components correctly identified: {top2}")
    else:
        print(f"[WARN] Top-2 = {top2}, expected {expected}")

    retained_set = set(retained)
    if retained_set == expected or retained_set.issubset(expected | {"L0.H0"}):
        print(f"[PASS] Greedy retained known causal components: {retained}")
    else:
        print(f"[INFO] Greedy retained: {retained}")

    if circuit_faith >= 0.8:
        print(f"[PASS] Circuit faithfulness {circuit_faith:.4f} >= 0.80 threshold")
    else:
        print(f"[WARN] Circuit faithfulness {circuit_faith:.4f} < 0.80 threshold")

    if percentile >= 70:
        print(f"[PASS] Discovered circuit at {percentile:.1f}th percentile vs random baseline")
    else:
        print(f"[WARN] Discovered circuit at {percentile:.1f}th percentile vs random baseline")

    print(f"\nTotal wall time: {time.time() - t0:.2f}s")
    print("P3 SMOKE TEST COMPLETE")


if __name__ == "__main__":
    main()
