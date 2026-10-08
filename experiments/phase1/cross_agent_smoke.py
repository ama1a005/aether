"""
P4 Smoke Test: Cross-Agent Causal Graph and Intervention
=========================================================
Demonstrates:
- CrossAgentGraph with sender/message/receiver node types
- SyntheticCausalBenchmark -- known causal path: S1->S2->M1->R2->Y
  (irrelevant nodes Sx, Mx, Rx have zero causal effect)
- CrossAgentGreedyPruner discovering the causal circuit
- Ground-truth circuit evaluation: precision, recall, F1, bridge localization
- Message patch intervention: patching M1 causes score drop
- Sender intervention: ablating S1 causes score drop
- Receiver intervention: ablating R2 causes score drop
- Irrelevant nodes: ablating Sx/Mx/Rx causes <0.02 score change
- Comparison table: sender vs message vs receiver intervention

Run: python -m experiments.phase1.cross_agent_smoke
"""

from __future__ import annotations
import os
import csv
import json
import time
import datetime

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from causal.validation.synthetic_benchmark import SyntheticCausalBenchmark
from causal.candidate_graph.cross_agent_graph import CrossAgentGraph
from discovery.greedy.cross_agent_pruner import CrossAgentGreedyPruner
from causal.bridge.intervention import CrossAgentInterventionRunner
from contracts.schemas import CircuitResult

EXPERIMENT_ID = f"P0_cross_{datetime.date.today().strftime('%Y%m%d')}_cross_agent_smoke_0"
SEED = 42


def visualize_graph(
    graph: CrossAgentGraph,
    retained_ids: list[str],
    save_path: str,
) -> None:
    """Visualize the cross-agent graph with nodes colored by region."""
    region_color = {
        "sender": "#4e9af1",
        "message": "#f1a74e",
        "receiver": "#5dc65a",
        "outcome": "#e05c5c",
    }
    region_x = {"sender": 0.15, "message": 0.45, "receiver": 0.75, "outcome": 0.92}

    nodes = list(graph.nodes.values())
    by_region: dict[str, list] = {}
    for nd in nodes:
        by_region.setdefault(nd["region"], []).append(nd)

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    node_positions: dict[str, tuple[float, float]] = {}
    for region, nds in by_region.items():
        x = region_x.get(region, 0.5)
        n = len(nds)
        for i, nd in enumerate(nds):
            y = 0.1 + (0.8 * (i + 0.5) / n)
            node_positions[nd["id"]] = (x, y)
            is_retained = nd["id"] in retained_ids
            color = region_color.get(region, "#cccccc")
            box_alpha = 1.0 if is_retained else 0.3
            ax.add_patch(mpatches.FancyBboxPatch(
                (x - 0.055, y - 0.04), 0.11, 0.08,
                boxstyle="round,pad=0.01",
                facecolor=color, edgecolor="black" if is_retained else "#aaaaaa",
                linewidth=2.0 if is_retained else 0.8,
                alpha=box_alpha, zorder=3,
            ))
            ax.text(x, y, nd["id"], ha="center", va="center", fontsize=9,
                    fontweight="bold" if is_retained else "normal",
                    color="black" if is_retained else "#888888", zorder=4)

    for edge in graph.edges:
        src, dst = edge["src"], edge["dst"]
        if src not in node_positions or dst not in node_positions:
            continue
        x0, y0 = node_positions[src]
        x1, y1 = node_positions[dst]
        both_retained = src in retained_ids and dst in retained_ids
        ax.annotate(
            "", xy=(x1 - 0.056, y1), xytext=(x0 + 0.056, y0),
            arrowprops=dict(
                arrowstyle="->",
                color="#cc4444" if edge.get("bridge") else ("#333333" if both_retained else "#cccccc"),
                lw=2.5 if both_retained else 0.8,
            ),
            zorder=2,
        )

    # Legend
    for region, color in region_color.items():
        ax.add_patch(mpatches.Rectangle((0, 0), 0, 0, color=color, label=region.title()))
    ax.legend(loc="lower right", fontsize=8, framealpha=0.8)
    ax.set_title(
        f"P4 Cross-Agent Causal Graph\n"
        f"Blue=Retained, Faded=Pruned, Red-arrow=Bridge edge\n"
        f"{EXPERIMENT_ID}",
        fontsize=10,
    )
    fig.tight_layout()
    fig.savefig(save_path, dpi=150)
    plt.close(fig)


def print_table(rows: list[dict], cols: list[str]) -> None:
    widths = {c: max(len(c), max(len(str(r.get(c, ""))) for r in rows)) for c in cols}
    header = "  ".join(f"{c:<{widths[c]}}" for c in cols)
    sep    = "  ".join("-" * widths[c] for c in cols)
    print(sep)
    print(header)
    print(sep)
    for r in rows:
        print("  ".join(f"{str(r.get(c,'')):<{widths[c]}}" for c in cols))
    print(sep)


def main() -> None:
    np.random.seed(SEED)
    os.makedirs("results/raw", exist_ok=True)
    os.makedirs("results/figures", exist_ok=True)

    t0 = time.time()

    print(f"\n{'='*65}")
    print(f"EXPERIMENT: {EXPERIMENT_ID}")
    print(f"{'='*65}")

    # ------------------------------------------------------------------
    # 1. Setup benchmark and graph
    # ------------------------------------------------------------------
    bench = SyntheticCausalBenchmark()
    graph = bench.build_candidate_graph()

    print(f"\nCandidate graph: {graph.node_count_by_region()}")
    print(f"Ground-truth causal path: {bench.get_ground_truth_causal_nodes()}")
    print(f"Ground-truth bridge nodes: {bench.get_ground_truth_bridge_nodes()}")

    # Full-graph score (all nodes active = 1.0)
    all_acts = {n: 1.0 for n in bench.nodes}
    full_score = bench.compute_score(all_acts)
    null_score = bench.compute_score({})  # all zeroed → score = 0

    def score_fn(retained_node_ids: list[str]) -> float:
        """Faithfulness: how well does the retained sub-circuit reproduce the full score?"""
        acts = {n: 1.0 for n in retained_node_ids}
        circuit_score = bench.compute_score(acts)
        if abs(full_score) < 1e-9:
            return 1.0 if abs(circuit_score) < 1e-9 else 0.0
        return float(np.clip(
            1.0 - abs(full_score - circuit_score) / (abs(full_score) + 1e-6),
            0.0, 1.0,
        ))

    # ------------------------------------------------------------------
    # 2. Cross-agent greedy pruning
    # ------------------------------------------------------------------
    pruner = CrossAgentGreedyPruner(graph, score_fn)
    retained, pruning_history = pruner.prune(faithfulness_threshold=0.80)
    eval_metrics = bench.evaluate_recovered_circuit(retained)

    print(f"\n{'-'*65}")
    print("CIRCUIT DISCOVERY -- Pruning History")
    print(f"{'-'*65}")
    print(f"{'Step':>4} {'Removed':>8} {'N_Left':>8} {'Faithfulness':>14} {'Region':>10}")
    print(f"{'-'*65}")
    for step_i, removed, n_left, faith, region in pruning_history:
        print(f"{step_i:>4} {removed:>8} {n_left:>8} {faith:>14.4f} {region:>10}")

    print(f"\nDiscovered circuit ({len(retained)} nodes): {retained}")

    # ------------------------------------------------------------------
    # 3. Ground-truth evaluation
    # ------------------------------------------------------------------
    print(f"\n{'-'*65}")
    print("GROUND-TRUTH CIRCUIT EVALUATION")
    print(f"{'-'*65}")
    eval_rows = [
        {"Metric": "Precision",                  "Value": f"{eval_metrics['precision']:.4f}"},
        {"Metric": "Recall",                      "Value": f"{eval_metrics['recall']:.4f}"},
        {"Metric": "F1",                          "Value": f"{eval_metrics['f1']:.4f}"},
        {"Metric": "Bridge Localization Accuracy","Value": f"{eval_metrics['bridge_localization_accuracy']:.4f}"},
        {"Metric": "False Positive Rate",         "Value": f"{eval_metrics['false_positive_rate']:.4f}"},
    ]
    print_table(eval_rows, ["Metric", "Value"])

    f1_score = eval_metrics["f1"]
    bridge_acc = eval_metrics["bridge_localization_accuracy"]

    # ------------------------------------------------------------------
    # 4. Intervention comparison: sender / message / receiver
    # ------------------------------------------------------------------
    print(f"\n{'-'*65}")
    print("INTERVENTION COMPARISON: sender vs message vs receiver")
    print(f"{'-'*65}")

    # score_fn with attacked message (M1=1.0) → baseline = full_score
    def receiver_score_fn(msg_acts: dict) -> float:
        acts = {"S1": 1.0, "S2": 1.0, "R2": 1.0}
        acts.update(msg_acts)
        return bench.compute_score(acts)

    def sender_intervention_fn(comp_id: str, operator: str, clean_acts: dict) -> dict:
        """Ablating sender component S1 zeroes it, reducing downstream message."""
        return {"M1": 0.0 if comp_id == "S1" else 1.0, "Mx": 1.0}

    def receiver_intervention_fn(comp_id: str, operator: str, clean_acts: dict, attacked_msg: dict) -> float:
        acts = {"S1": 1.0, "S2": 1.0, "M1": attacked_msg.get("M1", 1.0)}
        acts[comp_id] = 0.0  # ablate receiver component
        return bench.compute_score(acts)

    attacked_message_acts = {"M1": 1.0, "Mx": 1.0}

    runner = CrossAgentInterventionRunner(
        graph=graph,
        intervention_fn=sender_intervention_fn,
        message_record=attacked_message_acts,
        receiver_score_fn=receiver_score_fn,
        receiver_intervention_fn=receiver_intervention_fn,
    )

    # Message patch: M1 attacked→clean (0.0 nullifies causal bridge)
    s_b_msg, s_a_msg = runner.run_message_patch(
        attacked_message={"M1": 1.0},
        clean_message={"M1": 0.0},
        field_path="M1",
    )
    # Sender ablation: S1
    s_b_snd, s_a_snd = runner.run_sender_intervention("S1", "zero_ablation", {"S1": 1.0})
    # Receiver ablation: R2
    s_b_rec, s_a_rec = runner.run_receiver_intervention("R2", "zero_ablation", {"R2": 1.0}, {"M1": 1.0})

    # Irrelevant nodes -- verify no causal effect
    acts_full = {n: 1.0 for n in bench.nodes}
    irrel_rows = []
    for irr in ["Sx", "Mx", "Rx"]:
        acts_ablated = dict(acts_full)
        acts_ablated[irr] = 0.0
        score_before = bench.compute_score(acts_full)
        score_after  = bench.compute_score(acts_ablated)
        delta = abs(score_before - score_after)
        irrel_rows.append({"node": irr, "delta": delta, "is_causal": delta > 0.02})
        assert delta < 0.02, f"Irrelevant node {irr} caused delta={delta:.4f} > 0.02!"

    interv_rows = runner.intervention_records
    print_table(
        [{
            "Location": r["intervention_location"],
            "Component": r["component_id"],
            "Before": f"{r['score_before']:.4f}",
            "After": f"{r['score_after']:.4f}",
            "Delta": f"{r['delta']:+.4f}",
            "Causal": str(r["is_causal"]),
        } for r in interv_rows],
        ["Location", "Component", "Before", "After", "Delta", "Causal"],
    )

    print(f"\nIrrelevant nodes (must have |delta| < 0.02):")
    for row in irrel_rows:
        status = "PASS" if not row["is_causal"] else "FAIL"
        print(f"  [{status}] {row['node']}: delta={row['delta']:.6f}")

    # ------------------------------------------------------------------
    # 5. Random baseline comparison
    # ------------------------------------------------------------------
    k = len(retained)
    rand_mean, rand_std = pruner.compute_random_baseline(k=k, n_samples=200, seed=SEED)
    discovered_faith = score_fn(retained)
    percentile = (
        sum(
            1 for _ in range(200)
            if score_fn(
                list(np.random.default_rng(SEED + _ + 1).choice(
                    list(bench.nodes.keys()), size=min(k, len(bench.nodes)), replace=False
                ))
            ) < discovered_faith
        )
        / 200
        * 100
    )
    print(f"\nRandom baseline (k={k}, n=200): mean={rand_mean:.4f}, std={rand_std:.4f}")
    print(f"Discovered circuit faithfulness: {discovered_faith:.4f}")
    print(f"Circuit at ~{percentile:.1f}th percentile vs random matched-size")

    # ------------------------------------------------------------------
    # 6. Save outputs
    # ------------------------------------------------------------------
    # Intervention CSV
    intv_path = "results/raw/p4_smoke_intervention_results.csv"
    with open(intv_path, "w", newline="") as f:
        fieldnames = ["intervention_location", "component_id",
                      "score_before", "score_after", "delta", "is_causal"]
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(interv_rows)
    print(f"\nSaved: {intv_path}")

    # CircuitResult JSON
    circuit_result = CircuitResult(
        experiment_id=EXPERIMENT_ID,
        source_attack_ids=["synthetic_benchmark"],
        nodes=[
            {"id": n, "type": graph.nodes[n]["type"], "region": graph.nodes[n]["region"], "retained": True}
            for n in retained
        ],
        edges=[
            e for e in graph.edges
            if e["src"] in retained and e["dst"] in retained
        ],
        faithfulness=round(discovered_faith, 6),
        necessity=None,
        size=len(retained),
        benign_damage=0.0,
        search_method="greedy",
        search_cost={
            "n_candidates": len(bench.nodes),
            "n_forward_passes": len(pruning_history) * len(bench.nodes),
            "wall_time_s": round(time.time() - t0, 2),
        },
        metadata={
            "experiment_id": EXPERIMENT_ID,
            "seed": SEED,
            "benchmark": "SyntheticCausalBenchmark",
            "ground_truth_path": ["S1", "S2", "M1", "R2", "Y"],
            "evaluation": eval_metrics,
            "random_baseline_mean": round(rand_mean, 6),
            "random_baseline_std": round(rand_std, 6),
            "fixture_only": True,
        },
    )
    circuit_path = "results/raw/p4_smoke_circuit_result.json"
    with open(circuit_path, "w") as f:
        f.write(circuit_result.to_json())
    print(f"Saved: {circuit_path}")

    # Graph visualization
    graph_path = "results/figures/p4_graph.png"
    visualize_graph(graph, retained, graph_path)
    print(f"Saved: {graph_path}")

    # ------------------------------------------------------------------
    # 7. Final verification
    # ------------------------------------------------------------------
    print(f"\n{'='*65}")
    print("FINAL VERIFICATION")
    print(f"{'='*65}")
    checks = [
        ("F1 > 0.70", f1_score > 0.70, f"F1={f1_score:.4f}"),
        ("Bridge correctly localized", bridge_acc == 1.0, f"bridge_acc={bridge_acc:.4f}"),
        ("Message patch is causal (delta > 0.5)", abs(s_a_msg - s_b_msg) > 0.5,
         f"delta={abs(s_a_msg - s_b_msg):.4f}"),
        ("Sender ablation is causal", abs(s_a_snd - s_b_snd) > 0.5,
         f"delta={abs(s_a_snd - s_b_snd):.4f}"),
        ("Receiver ablation is causal", abs(s_a_rec - s_b_rec) > 0.5,
         f"delta={abs(s_a_rec - s_b_rec):.4f}"),
        ("Irrelevant nodes non-causal", all(not r["is_causal"] for r in irrel_rows),
         f"{[r['node'] for r in irrel_rows if r['is_causal']]} should be empty"),
        ("Circuit faithfulness >= 0.80", discovered_faith >= 0.80,
         f"faithfulness={discovered_faith:.4f}"),
    ]

    all_pass = True
    for label, ok, detail in checks:
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {label} -- {detail}")
        if not ok:
            all_pass = False

    print(f"\nTotal wall time: {time.time() - t0:.2f}s")
    print(f"\n{'='*65}")
    if all_pass:
        print("PASS -- P4 CROSS-AGENT SMOKE TEST COMPLETE")
    else:
        print("PARTIAL PASS -- some checks failed, see above")
    print(f"{'='*65}")


if __name__ == "__main__":
    main()
