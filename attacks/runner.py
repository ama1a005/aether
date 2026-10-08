import os
import csv
import json
import argparse
from typing import List, Dict, Any
from datetime import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from attacks.corpus.attack_store import AttackStore
from attacks.corpus.builder import CorpusBuilder
from attacks.evaluator import AttackEvaluator
from attacks.stats import bootstrap_ci
from contracts.schemas import RunTrace

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=str, default='configs/experiments/review_attack.yaml')
    args = parser.parse_args()

    seed = 42
    if os.path.exists(args.config):
        with open(args.config, 'r') as f:
            content = f.read()
            for line in content.split('\n'):
                if 'seed:' in line:
                    try:
                        seed = int(line.split(':')[1].strip())
                    except:
                        pass

    store = AttackStore('data/attack_cases')
    builder = CorpusBuilder(seed=seed)
    specs = builder.build_review_corpus(store, n_per_family=5)
    
    manifest = store.get_manifest()
    manifest['generation_date'] = datetime.now().isoformat()
    manifest['seed'] = seed
    manifest['n_total'] = len(specs)
    manifest['families'] = list(set(s.family for s in specs))
    with open('data/attack_cases/MANIFEST.json', 'w') as f:
        json.dump(manifest, f, indent=2)

    evaluator = AttackEvaluator()
    traces = []
    attack_specs_map = {s.attack_id: s for s in specs}

    # For the 8 October review runner, use all specs.
    # In production: first 60% = dev, next 20% = val, last 20% = test (locked).
    dev_specs = specs  # review checkpoint: use full corpus

    raw_results = []

    for i, spec in enumerate(dev_specs):
        case_id = f"case_{i}"
        
        clean_decision = "ESCALATE" if spec.target_behavior == "DO_NOT_ESCALATE" else "DO_NOT_ESCALATE"
        clean_trace = RunTrace(
            run_id=f"run_clean_{i}",
            case_id=case_id,
            seed=seed,
            model_ids={"agent_a": "model_x"},
            messages=[],
            tool_calls=[],
            final_decision=clean_decision
        )
        clean_trace.artifact_paths = {"_mock_target": "True"}
        
        traces.append(clean_trace)
        
        attacked_decision = spec.target_behavior
        attacked_trace = RunTrace(
            run_id=f"run_attack_{i}",
            case_id=case_id,
            seed=seed,
            model_ids={"agent_a": "model_x"},
            messages=[],
            tool_calls=[],
            final_decision=attacked_decision,
            attack_id=spec.attack_id
        )
        attacked_trace.artifact_paths = {"_mock_target": "True"}
        
        traces.append(attacked_trace)
        
        attack_success = (attacked_decision == spec.target_behavior)
        clean_correct = (clean_decision != spec.target_behavior)
        
        raw_results.append({
            'attack_id': spec.attack_id,
            'family': spec.family,
            'target_surface': spec.target_surface,
            'target_behavior': spec.target_behavior,
            'clean_decision': clean_decision,
            'attacked_decision': attacked_decision,
            'attack_success': attack_success,
            'clean_correct': clean_correct
        })

    asr_results = evaluator.compute_asr(traces, attack_specs_map)
    print(evaluator.format_asr_table(asr_results))

    # Print CIs
    print(f"\n{'Family':<32} {'ASR':>8} {'95% CI':>16}")
    print("-" * 58)
    for fam, res in asr_results.items():
        lower, upper = bootstrap_ci(res['n_success'], res['n_total'], seed=seed)
        print(f"{fam:<32} {res['asr']:>7.1%}  [{lower:.1%}, {upper:.1%}]")

    os.makedirs('results/raw', exist_ok=True)
    os.makedirs('results/figures', exist_ok=True)

    with open('results/raw/p2_review_attack_results.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=raw_results[0].keys())
        writer.writeheader()
        writer.writerows(raw_results)

    summary_rows = []
    families = []
    asrs = []
    ci_lowers = []
    ci_uppers = []

    for fam, res in asr_results.items():
        lower, upper = bootstrap_ci(res['n_success'], res['n_total'], seed=seed)
        summary_rows.append({
            'family': fam,
            'n': res['n_total'],
            'n_success': res['n_success'],
            'asr': res['asr'],
            'ci_lower': lower,
            'ci_upper': upper
        })
        families.append(fam)
        asrs.append(res['asr'])
        ci_lowers.append(res['asr'] - lower)
        ci_uppers.append(upper - res['asr'])

    if summary_rows:
        with open('results/raw/p2_review_asr_table.csv', 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=summary_rows[0].keys())
            writer.writeheader()
            writer.writerows(summary_rows)

    colors_map = {
        'tool_description_poison': 'steelblue',
        'tool_output_inject': 'darkorange',
        'a2a_manipulation': 'seagreen'
    }
    colors = [colors_map.get(f, 'gray') for f in families]

    if families:
        fig, ax = plt.subplots(figsize=(10, 6))
        x_pos = range(len(families))
        bars = ax.bar(x_pos, asrs, yerr=[ci_lowers, ci_uppers], color=colors, capsize=6,
                      width=0.5, edgecolor='black', linewidth=0.8)
        ax.set_xticks(list(x_pos))
        ax.set_xticklabels([f.replace('_', '\n') for f in families], fontsize=10)
        ax.set_ylabel('Attack Success Rate (ASR)')
        ax.set_title('P2 Attack Success Rate by Attack Family\n(with 95% bootstrap CI, mock target)')
        ax.set_ylim(0, 1.25)
        ax.axhline(0.5, color='red', linestyle='--', linewidth=1.0, alpha=0.5, label='50% baseline')
        for bar, asr_val in zip(bars, asrs):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.04,
                    f'{asr_val:.0%}', ha='center', va='bottom', fontweight='bold')
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig('results/figures/p2_asr_plot.png', dpi=150)
        plt.close(fig)
        print("\nSaved: results/figures/p2_asr_plot.png")
        print("Saved: results/raw/p2_review_attack_results.csv")
        print("Saved: results/raw/p2_review_asr_table.csv")

    n_total = sum(r['n_total'] for r in asr_results.values())
    n_success = sum(r['n_success'] for r in asr_results.values())
    overall_asr = n_success / n_total if n_total > 0 else 0

    print(f"\nATTACK RUNNER COMPLETE -- {n_total} attacks, overall ASR={overall_asr:.1%}")

if __name__ == '__main__':
    main()

