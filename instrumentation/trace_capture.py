import torch
from typing import Dict, Tuple
from .hooks.hook_registry import HookRegistry

class TraceCapture:
    def __init__(self, model: torch.nn.Module, hook_registry: HookRegistry):
        self.model = model
        self.hook_registry = hook_registry

    def capture(self, input_ids: torch.Tensor, run_id: str) -> Tuple[Any, Dict[str, torch.Tensor]]:
        self.hook_registry.activations.clear()
        with torch.no_grad():
            output = self.model(input_ids)
            
        activations = {k: v.clone() for k, v in self.hook_registry.get_activations().items()}
        return output, activations
