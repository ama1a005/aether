import torch
import torch.nn as nn
from typing import Dict

class HookRegistry:
    def __init__(self, model: nn.Module):
        self.model = model
        self.hooks = {}
        self.activations: Dict[str, torch.Tensor] = {}

    def register(self, component_id: str, module_path: str):
        module = self.model
        if module_path:
            for part in module_path.split('.'):
                module = getattr(module, part)
        
        def hook_fn(mod, inputs, outputs):
            # Capture output
            out = outputs[0] if isinstance(outputs, tuple) else outputs
            self.activations[component_id] = out.clone().detach()
            
        handle = module.register_forward_hook(hook_fn)
        self.hooks[component_id] = handle

    def remove_all(self):
        for handle in self.hooks.values():
            handle.remove()
        self.hooks.clear()

    def get_activations(self) -> Dict[str, torch.Tensor]:
        return self.activations
