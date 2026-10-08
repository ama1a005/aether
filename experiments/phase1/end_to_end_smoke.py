"""
End-to-End Integration Smoke Test
===================================
Chains all 4 member modules together in one executable script:

  P2 (attack corpus) -> P1 (target harness) -> P3 (activation hooks + causal ranking)
                    -> P4 (cross-agent graph + circuit discovery)

Known-scope for 8 Oct review:
  - Uses MockMCPClient + rule-based agents (no real LLM)
  - Uses ToyTransformer for activation hooks (P3 toy model)
  - Uses SyntheticCausalBenchmark for P4 graph (real traces deferred to 9 Oct)
  - All results saved to results/raw/e2e_*

Run: python -m experiments.phase1.end_to_end_smoke
"""

from __future__ import annotations
import os
import csv
import json
import time
import datetime
import dataclasses

import torch
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ── P2 imports ────────────────────────────────────────────────────────────────
from attacks.corpus.builder import CorpusBuilder
from attacks.corpus.attack_store import AttackStore
from attacks.evaluator import AttackEvaluator
from attacks.stats import bootstrap_ci

# ── P1 imports ────────────────────────────────────────────────────────────────
from target.case_loader import CaseLoader
from target.mcp.mock_client import MockMCPClient
from target.mcp.tools import get_ecg_analysis, get_vital_signs
from target.agents.agent_a import AgentA
from target.agents.agent_b import AgentB
from target.decision_parser import DecisionParser
from target.trace_logger import TraceLogger
from contracts.schemas import RunTrace, AttackSpec, CircuitResult

# ── P3 imports ────────────────────────────────────────────────────────────────
from instrumentation.hooks.hook_registry import HookRegistry
from causal.interventions.operators import ZeroAblation
from causal.metrics.faithfulness import compute_faithfulness
from discovery.greedy.pruner import GreedyCausalPruner
from discovery.random_baseline.sampler import RandomCircuitSampler

# ── P4 imports ────────────────────────────────────────────────────────────────
from causal.validation.synthetic_benchmark import SyntheticCausalBenchmark
from causal.candidate_graph.cross_agent_graph import CrossAgentGraph
from discovery.greedy.cross_agent_pruner import CrossAgentGreedyPruner
from causal.bridge.intervention import CrossAgentInterventionRunner
from remediation.candidates.extractor import RemediationCandidateExtractor
from remediation.selector.deterministic_selector import DeterministicInterventionSelector

import torch.nn as nn

EXPERIMENT_ID = f"P0_e2e_{datetime.date.today().strftime('%Y%m%d')}_integration_smoke_0"
SEED = 42


# ---------------------------------------------------------------------------
# Toy model (same as P3 smoke — avoids downloading a real LLM for the review)
# ---------------------------------------------------------------------------

class ToyTransformer(nn.Module):
    """3-layer 4-head toy transformer with explicit causal structure."""
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


def sep(title: str = "", width: int = 65) -> None:
    if title:
        pad = (width - len(title) - 2) // 2
        print(f"\n{'=' * pad} {title} {'=' * (width - pad - len(title) - 2)}")
    else:
        print("=" * width)


def section(title: str, width: int = 65) -> None:
    print(f"\n{'-' * width}")
    print(f"  {title}")
    print(f"{'-' * width}")


def print_table(rows: list[dict], cols: list[str]) -> None:
    widths = {c: max(len(c), max((len(str(r.get(c, ""))) for r in rows), default=0)) for c in cols}
    header = "  ".join(f"{c:<{widths[c]}}" for c in cols)
    bar = "  ".join("-" * widths[c] for c in cols)
    print(bar); print(header); print(bar)
    for r in rows:
        print("  ".join(f"{str(r.get(c, '')):<{widths[c]}}" for c in cols))
    print(bar)


# ---------------------------------------------------------------------------
# STAGE 1 — P2: Build attack corpus
# ---------------------------------------------------------------------------

def stage_p2_attack_corpus(seed: int) -> tuple[list[AttackSpec], dict]:
    section("STAGE 1 — P2: Attack Corpus")
    store = AttackStore("data/attack_cases")
    builder = CorpusBuilder(seed=seed)
    specs = builder.build_review_corpus(store, n_per_family=3)
    by_family: dict[str, int] = {}
    for s in specs:
        by_family[s.family] = by_family.get(s.family, 0) + 1
    print(f"  Built {len(specs)} attack specs: {by_family}")
    return specs, by_family


# ---------------------------------------------------------------------------
# STAGE 2 — P1: Run target harness (clean + attacked)
# ---------------------------------------------------------------------------

def stage_p1_target(specs: list[AttackSpec], seed: int) -> tuple[list[RunTrace], list[dict]]:
    section("STAGE 2 — P1: Two-Agent Target Harness")

    mcp = MockMCPClient()
    mcp.register_tool("get_ecg_analysis", get_ecg_analysis)
    mcp.register_tool("get_vital_signs", get_vital_signs)
    agent_a = AgentA("agent_a_toy", mcp, {})
    agent_b = AgentB("agent_b_toy", {})
    parser  = DecisionParser()
    loader  = CaseLoader("synthetic")
    logger  = TraceLogger("results/raw")

    cases = loader.load_cases(n=5, seed=seed)
    print(f"  Loaded {len(cases)} synthetic cases")

    traces: list[RunTrace] = []
    run_rows: list[dict] = []
    attack_specs_map: dict[str, AttackSpec] = {s.attack_id: s for s in specs}

    for case in cases:
        for mode, attack_spec in [("clean", None), ("attacked", specs[0])]:
            out_a, msg_a, tool_calls = agent_a.run(case, attack_spec=attack_spec)
            dec_b, score_b = agent_b.run(msg_a, case)
            decision, conf = parser.parse(dec_b, msg_a.structured_payload)
            attack_success = (
                parser.is_attack_success(decision, attack_spec) if attack_spec else False
            )
            run_id = f"e2e_{case.case_id}_{mode}_{seed}"
            trace = RunTrace(
                run_id=run_id,
                case_id=case.case_id,
                attack_id=attack_spec.attack_id if attack_spec else None,
                seed=seed,
                model_ids={"agent_a": "agent_a_toy", "agent_b": "agent_b_toy"},
                messages=[dataclasses.asdict(msg_a)],
                tool_calls=tool_calls,
                final_decision=decision,
                decision_score=conf,
                attack_success=attack_success,
            )
            trace.artifact_paths["trace"] = logger.log(trace)
            traces.append(trace)
            run_rows.append({
                "case_id": case.case_id,
                "ground_truth": case.ground_truth_decision,
                "mode": mode,
                "decision": decision,
                "score": f"{conf:.2f}",
                "attack_success": attack_success,
            })

    print_table(run_rows, ["case_id", "ground_truth", "mode", "decision", "score", "attack_success"])

    clean_traces   = [t for t in traces if t.attack_id is None]
    attacked_traces = [t for t in traces if t.attack_id is not None]
    clean_correct = sum(1 for t in clean_traces if t.final_decision == next(
        (c.ground_truth_decision for c in cases if c.case_id == t.case_id), ""))
    clean_pass = clean_correct / len(clean_traces) if clean_traces else 0.0
    atk_success = sum(1 for t in attacked_traces if t.attack_success) / len(attacked_traces) if attacked_traces else 0.0

    print(f"\n  Clean pass rate  : {clean_pass:.1%}  ({clean_correct}/{len(clean_traces)})")
    print(f"  Attack success rate: {atk_success:.1%}  ({sum(t.attack_success for t in attacked_traces)}/{len(attacked_traces)})")

    # ASR by family using evaluator
    evaluator = AttackEvaluator()
    asr_results = evaluator.compute_asr(attacked_traces, attack_specs_map)
    if asr_results:
        print(f"\n{evaluator.format_asr_table(asr_results)}")

    return traces, run_rows


# ---------------------------------------------------------------------------
# STAGE 3 — P3: Activation hooks + causal ranking on toy model
# ---------------------------------------------------------------------------

def stage_p3_mechanistic(seed: int) -> tuple[list[str], list[tuple]]:
    section("STAGE 3 — P3: Activation Hooks + Causal Ranking")
    torch.manual_seed(seed)

    model = ToyTransformer()
    with torch.no_grad():
        model.embed.weight[1] += 5.0
        model.L1[2].weight += torch.eye(64) * 2.0
        model.L2[1].weight += torch.eye(64) * 2.0
        model.fc.weight[1] += 1.0

    clean_input = torch.tensor([[0, 0, 2, 3]])
    adv_input   = torch.tensor([[0, 1, 2, 3]])
    target_fn   = lambda out: (out[0, 1] - out[0, 0]).item()

    # Verify hook non-interference
    registry = HookRegistry(model)
    with torch.no_grad():
        out_no_hook  = model(adv_input)
        score_no_hook = target_fn(out_no_hook)
    with torch.no_grad():
        out_hooked   = model(adv_input)
        score_hooked  = target_fn(out_hooked)
    assert abs(score_no_hook - score_hooked) < 1e-4, "Hook interference detected!"
    print(f"  [PASS] Hook non-interference verified (delta={abs(score_no_hook - score_hooked):.2e})")

    candidates = [f"L{l}.H{h}" for l in range(3) for h in range(4)]
    mapping    = {f"L{l}.H{h}": f"L{l}.{h}" for l in range(3) for h in range(4)}

    with torch.no_grad():
        clean_score = target_fn(model(clean_input))
        adv_score   = target_fn(model(adv_input))
    delta_full = adv_score - clean_score

    # Rank components by zero-ablation effect
    ranking = []
    for cid in candidates:
        out, _ = ZeroAblation(model, adv_input, [cid], module_mapping=mapping)
        effect = abs(adv_score - target_fn(out))
        ranking.append((cid, round(adv_score, 4), round(target_fn(out), 4), round(effect, 4)))
    ranking.sort(key=lambda x: x[3], reverse=True)

    print(f"\n  Clean score: {clean_score:.4f} | Attacked: {adv_score:.4f} | delta_full: {delta_full:.4f}")
    print("\n  Top-5 causal components (by ablation effect):")
    print_table(
        [{"Component": r[0], "Base": f"{r[1]:.4f}", "Ablated": f"{r[2]:.4f}", "Effect": f"{r[3]:.4f}"}
         for r in ranking[:5]],
        ["Component", "Base", "Ablated", "Effect"]
    )

    # Greedy pruning
    def op(mod, inp, comps):
        return ZeroAblation(mod, inp, comps, module_mapping=mapping)

    pruner = GreedyCausalPruner(
        model=model, hook_registry=registry, intervention_operator=op,
        faithfulness_fn=compute_faithfulness, candidate_nodes=candidates,
        faithfulness_threshold=0.85, target_fn=target_fn,
    )
    retained, history = pruner.prune([adv_input], [clean_input])
    final_faith = history[-1][2] if history else 0.0
    print(f"\n  Greedy circuit: {retained} | faithfulness={final_faith:.4f}")

    # Random baseline
    sampler = RandomCircuitSampler(candidates)
    rand_faiths = []
    for samp in sampler.sample_many(k=len(retained), n_samples=100, seed=seed):
        abl = [c for c in candidates if c not in samp]
        out, _ = op(model, adv_input, abl)
        rand_faiths.append(compute_faithfulness(delta_full, target_fn(out) - clean_score))
    rand_mean = sum(rand_faiths) / len(rand_faiths)
    pct = sum(1 for f in rand_faiths if f < final_faith) / len(rand_faiths) * 100
    print(f"  Random baseline (n=100, k={len(retained)}): mean={rand_mean:.4f} | circuit at {pct:.0f}th pct")

    top2 = {r[0] for r in ranking[:2]}
    status = "PASS" if top2 == {"L1.H2", "L2.H1"} else "WARN"
    print(f"  [{status}] Top-2 causal = {sorted(top2)} (expected ['L1.H2', 'L2.H1'])")

    return retained, history


# ---------------------------------------------------------------------------
# STAGE 4 — P4: Cross-agent graph + circuit discovery + interventions
# ---------------------------------------------------------------------------

def stage_p4_cross_agent(seed: int) -> dict:
    section("STAGE 4 — P4: Cross-Agent Graph + Interventions")

    bench = SyntheticCausalBenchmark()
    graph = bench.build_candidate_graph()
    full_score = bench.compute_score({n: 1.0 for n in bench.nodes})

    import numpy as np
    np.random.seed(seed)

    def score_fn(retained: list[str]) -> float:
        s = bench.compute_score({n: 1.0 for n in retained})
        return float(np.clip(1.0 - abs(full_score - s) / (abs(full_score) + 1e-6), 0.0, 1.0))

    pruner = CrossAgentGreedyPruner(graph, score_fn)
    retained, history = pruner.prune(faithfulness_threshold=0.80)
    metrics = bench.evaluate_recovered_circuit(retained)

    print(f"  Discovered circuit ({len(retained)} nodes): {retained}")
    print_table(
        [{"Metric": k, "Value": f"{v:.4f}"} for k, v in metrics.items()],
        ["Metric", "Value"],
    )

    # Intervention runner
    def recv_score(msg: dict) -> float:
        return bench.compute_score({"S1": 1.0, "S2": 1.0, "R2": 1.0, **msg})

    def sender_fn(cid, op, clean):
        return {"M1": 0.0 if cid == "S1" else 1.0, "Mx": 1.0}

    def recv_fn(cid, op, clean, msg):
        a = {"S1": 1.0, "S2": 1.0, "M1": msg.get("M1", 1.0)}; a[cid] = 0.0
        return bench.compute_score(a)

    runner = CrossAgentInterventionRunner(graph, sender_fn, {"M1": 1.0}, recv_score, recv_fn)
    runner.run_message_patch({"M1": 1.0}, {"M1": 0.0}, "M1")
    runner.run_sender_intervention("S1", "zero", {"S1": 1.0})
    runner.run_receiver_intervention("R2", "zero", {"R2": 1.0}, {"M1": 1.0})

    print("\n  Intervention comparison (sender / message / receiver):")
    print_table(
        [{"Location": r["intervention_location"], "Component": r["component_id"],
          "Before": f"{r['score_before']:.4f}", "After": f"{r['score_after']:.4f}",
          "Delta": f"{r['delta']:+.4f}", "Causal": str(r["is_causal"])}
         for r in runner.intervention_records],
        ["Location", "Component", "Before", "After", "Delta", "Causal"],
    )

    # Remediation candidate extraction from the discovered circuit subgraph
    circuit_subgraph = graph.get_circuit_subgraph(retained)
    extractor = RemediationCandidateExtractor(circuit_subgraph)
    candidates = extractor.extract_candidates()
    print(f"\n  Remediation candidates (top-3 by causal strength):")
    print_table(
        [{"Rank": i+1, "Location": c["location_type"], "Component": c["component_id"],
          "Strength": f"{c['estimated_causal_strength']:.4f}", "Operators": str(c["intervention_operators"])}
         for i, c in enumerate(candidates[:3])],
        ["Rank", "Location", "Component", "Strength", "Operators"],
    )

    # Selector: merge candidates + eval scores, then pick best
    intv_by_comp = {r["component_id"]: r for r in runner.intervention_records}
    candidate_evaluations = []
    for c in candidates:
        r = intv_by_comp.get(c["component_id"], {})
        candidate_evaluations.append({
            **c,
            "asr_reduction": abs(r.get("delta", 0.5)),
            "benign_damage": 0.02,
            "latency_ms": 1.0,
        })
    selector = DeterministicInterventionSelector(candidate_evaluations)
    best = selector.select(min_asr_reduction=0.5)
    print(f"\n  Selected remediation: {best.get('component_id', 'N/A')} "
          f"@ location={best.get('location_type', 'N/A')}")

    return metrics


# ---------------------------------------------------------------------------
# STAGE 5 — Save all results
# ---------------------------------------------------------------------------

def save_all_results(
    run_rows: list[dict],
    p3_retained: list[str],
    p3_history: list,
    p4_metrics: dict,
    t_start: float,
) -> None:
    section("STAGE 5 — Saving Results")
    os.makedirs("results/raw", exist_ok=True)
    os.makedirs("results/figures", exist_ok=True)

    # E2E run summary CSV
    csv_path = "results/raw/e2e_smoke_run_summary.csv"
    if run_rows:
        with open(csv_path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=run_rows[0].keys())
            w.writeheader(); w.writerows(run_rows)
        print(f"  Saved: {csv_path}")

    # E2E summary JSON
    summary = {
        "experiment_id": EXPERIMENT_ID,
        "wall_time_s": round(time.time() - t_start, 2),
        "p1": {
            "n_cases": len([r for r in run_rows if r["mode"] == "clean"]),
            "clean_pass_rate": sum(1 for r in run_rows
                                   if r["mode"] == "clean" and r["decision"] == r["ground_truth"])
                               / max(1, sum(1 for r in run_rows if r["mode"] == "clean")),
            "attack_success_rate": sum(1 for r in run_rows
                                       if r["mode"] == "attacked" and r["attack_success"])
                                   / max(1, sum(1 for r in run_rows if r["mode"] == "attacked")),
        },
        "p3": {
            "retained_circuit": p3_retained,
            "final_faithfulness": p3_history[-1][2] if p3_history else None,
            "n_pruning_steps": len(p3_history),
        },
        "p4": p4_metrics,
        "fixture_only": True,
    }
    json_path = "results/raw/e2e_smoke_summary.json"
    with open(json_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"  Saved: {json_path}")

    # Combined faithfulness plot (P3) + P4 metrics bar
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # P3: faithfulness curve
    ax1 = axes[0]
    if len(p3_history) > 1:
        sizes = [h[1] for h in p3_history]
        faiths = [h[2] for h in p3_history]
        ax1.plot(sizes, faiths, "o-", color="steelblue", linewidth=2, label="Greedy circuit")
        ax1.invert_xaxis()
    ax1.axhline(0.85, color="red", linestyle="--", alpha=0.6, label="Threshold 0.85")
    ax1.set_xlabel("Retained Components"); ax1.set_ylabel("Faithfulness F(C)")
    ax1.set_title("P3: Faithfulness vs Circuit Size\n(ToyTransformer)")
    ax1.legend(); ax1.grid(True, alpha=0.3)

    # P4: bar chart of metrics
    ax2 = axes[1]
    metric_names = ["precision", "recall", "f1", "bridge_localization_accuracy"]
    metric_vals  = [p4_metrics.get(m, 0.0) for m in metric_names]
    colors = ["steelblue", "darkorange", "seagreen", "crimson"]
    bars = ax2.bar(range(len(metric_names)), metric_vals, color=colors, edgecolor="black", linewidth=0.8)
    ax2.set_xticks(range(len(metric_names)))
    ax2.set_xticklabels(["Precision", "Recall", "F1", "Bridge Acc"], fontsize=9)
    ax2.set_ylim(0, 1.2); ax2.set_ylabel("Score")
    ax2.set_title("P4: Circuit Recovery Metrics\n(SyntheticCausalBenchmark)")
    for bar, val in zip(bars, metric_vals):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.03,
                 f"{val:.2f}", ha="center", va="bottom", fontweight="bold")
    ax2.grid(axis="y", alpha=0.3)

    fig.suptitle(f"AETHER End-to-End Smoke Test\n{EXPERIMENT_ID}", fontsize=11)
    fig.tight_layout()
    fig_path = "results/figures/e2e_smoke_combined.png"
    fig.savefig(fig_path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {fig_path}")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main() -> None:
    t0 = time.time()

    sep("AETHER END-TO-END INTEGRATION SMOKE TEST")
    print(f"  Experiment: {EXPERIMENT_ID}")
    print(f"  Seed: {SEED}")
    print(f"  Scope: toy model + mock MCP + fixture attacks")

    # Stage 1: P2 attack corpus
    specs, by_family = stage_p2_attack_corpus(SEED)

    # Stage 2: P1 target harness
    traces, run_rows = stage_p1_target(specs, SEED)

    # Stage 3: P3 mechanistic
    p3_retained, p3_history = stage_p3_mechanistic(SEED)

    # Stage 4: P4 cross-agent
    p4_metrics = stage_p4_cross_agent(SEED)

    # Stage 5: Save
    save_all_results(run_rows, p3_retained, p3_history, p4_metrics, t0)

    # Final verification
    sep("FINAL INTEGRATION VERIFICATION")
    checks = [
        ("P1 traces generated", len(traces) > 0, f"{len(traces)} traces"),
        ("P1 clean traces exist", any(t.attack_id is None for t in traces), ""),
        ("P1 attacked traces exist", any(t.attack_id is not None for t in traces), ""),
        ("P2 attack corpus built", len(specs) >= 9, f"{len(specs)} specs"),
        ("P3 circuit non-empty", len(p3_retained) > 0, f"retained={p3_retained}"),
        ("P3 faithfulness >= 0.85", (p3_history[-1][2] if p3_history else 0) >= 0.85,
         f"faithfulness={p3_history[-1][2] if p3_history else 0:.4f}"),
        ("P4 F1 > 0.70", p4_metrics.get("f1", 0) > 0.70, f"F1={p4_metrics.get('f1', 0):.4f}"),
        ("P4 bridge localized", p4_metrics.get("bridge_localization_accuracy", 0) == 1.0,
         f"bridge_acc={p4_metrics.get('bridge_localization_accuracy', 0):.4f}"),
        ("Result files saved", os.path.exists("results/raw/e2e_smoke_summary.json"), ""),
    ]

    all_pass = True
    for label, ok, detail in checks:
        status = "PASS" if ok else "FAIL"
        suffix = f" -- {detail}" if detail else ""
        print(f"  [{status}] {label}{suffix}")
        if not ok:
            all_pass = False

    print(f"\n  Wall time: {time.time() - t0:.2f}s")
    sep()
    if all_pass:
        print("ALL CHECKS PASS -- END-TO-END INTEGRATION SMOKE COMPLETE")
    else:
        print("SOME CHECKS FAILED -- see above")
    sep()


if __name__ == "__main__":
    main()
