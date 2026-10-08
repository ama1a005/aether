import os
import json
from typing import List
from contracts.schemas import RunTrace

class TraceLogger:
    def __init__(self, output_dir: str = 'results/raw'):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def log(self, trace: RunTrace) -> str:
        filepath = os.path.join(self.output_dir, f"trace_{trace.run_id}.json")
        with open(filepath, 'w') as f:
            f.write(trace.to_json())
        return filepath

    def load(self, run_id: str) -> RunTrace:
        filepath = os.path.join(self.output_dir, f"trace_{run_id}.json")
        with open(filepath, 'r') as f:
            data = json.load(f)
        return RunTrace.from_dict(data)

    def log_batch(self, traces: List[RunTrace]) -> List[str]:
        return [self.log(t) for t in traces]
