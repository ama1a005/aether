import matplotlib.pyplot as plt
import numpy as np
from typing import List

def faithfulness_size_report(pruning_history: List[tuple]) -> dict:
    if not pruning_history: return {}
    sizes = [x[2] for x in pruning_history]
    faithfulness = [x[3] for x in pruning_history]
    return {
        "start_size": sizes[0] if sizes else 0,
        "end_size": sizes[-1] if sizes else 0,
        "start_faithfulness": faithfulness[0] if faithfulness else 0,
        "end_faithfulness": faithfulness[-1] if faithfulness else 0,
        "removed_nodes_by_region": {
            "sender": len([x for x in pruning_history if x[4] == "sender"]),
            "message": len([x for x in pruning_history if x[4] == "message"]),
            "receiver": len([x for x in pruning_history if x[4] == "receiver"]),
        }
    }

def random_baseline_percentile(discovered_faithfulness: float, random_faithfulnesses: List[float]) -> float:
    if not random_faithfulnesses: return 0.0
    arr = np.array(random_faithfulnesses)
    return float(np.mean(discovered_faithfulness >= arr))

def plot_faithfulness_curve(pruning_history: List[tuple], random_baseline_mean: float, random_baseline_std: float, save_path: str):
    sizes = [x[2] for x in pruning_history]
    faithfulness = [x[3] for x in pruning_history]
    
    plt.figure()
    plt.plot(sizes, faithfulness, label='Discovered Circuit', marker='o')
    plt.axhline(random_baseline_mean, color='r', linestyle='--', label='Random Baseline Mean')
    plt.fill_between(sizes, random_baseline_mean - random_baseline_std, random_baseline_mean + random_baseline_std, color='r', alpha=0.2, label='+/- 1 std')
    plt.xlabel('Number of Retained Nodes')
    plt.ylabel('Faithfulness Score')
    plt.title('Faithfulness vs Circuit Size')
    plt.legend()
    plt.savefig(save_path)
    plt.close()

def circuit_summary_table(circuit_result_dict: dict) -> str:
    lines = ["Circuit Summary", "="*20]
    for k, v in circuit_result_dict.items():
        lines.append(f"{k}: {v}")
    return "\n".join(lines)
