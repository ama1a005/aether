import torch
import torch.nn as nn
from typing import List, Dict, Any, Callable, Tuple
from contextlib import contextmanager

@contextmanager
def apply_hooks(model: nn.Module, hooks: List):
    handles = []
    for module_path, hook_fn in hooks:
        mod = model
        if module_path:
            for p in module_path.split('.'):
                mod = getattr(mod, p)
        handles.append(mod.register_forward_hook(hook_fn))
    try:
        yield
    finally:
        for h in handles:
            h.remove()

def ZeroAblation(model: nn.Module, input_ids: torch.Tensor, component_ids: List[str], **kwargs) -> Tuple[Any, Dict[str, str]]:
    hooks = []
    meta = {}
    
    # We need module path from component id. Assuming simple mapping or pass module_paths in kwargs.
    # For now, let's assume kwargs contains 'module_mapping': dict mapping component_id -> module_path
    module_mapping = kwargs.get('module_mapping', {})
    
    def get_zero_hook(cid):
        def hook_fn(mod, inputs, outputs):
            if isinstance(outputs, tuple):
                return (torch.zeros_like(outputs[0]),) + outputs[1:]
            return torch.zeros_like(outputs)
        return hook_fn

    for cid in component_ids:
        path = module_mapping.get(cid, cid) # fallback to cid as path
        hooks.append((path, get_zero_hook(cid)))
        meta[cid] = 'intervened'

    with apply_hooks(model, hooks):
        with torch.no_grad():
            output = model(input_ids)
            
    return output, meta

def MeanAblation(model: nn.Module, input_ids: torch.Tensor, component_ids: List[str], **kwargs) -> Tuple[Any, Dict[str, str]]:
    hooks = []
    meta = {}
    module_mapping = kwargs.get('module_mapping', {})
    means = kwargs.get('means', {}) # dict of component_id -> tensor mean
    
    def get_mean_hook(cid, mean_tensor):
        def hook_fn(mod, inputs, outputs):
            if isinstance(outputs, tuple):
                return (mean_tensor.expand_as(outputs[0]).clone(),) + outputs[1:]
            return mean_tensor.expand_as(outputs).clone()
        return hook_fn

    for cid in component_ids:
        path = module_mapping.get(cid, cid)
        mean_t = means[cid]
        hooks.append((path, get_mean_hook(cid, mean_t)))
        meta[cid] = 'intervened'

    with apply_hooks(model, hooks):
        with torch.no_grad():
            output = model(input_ids)
            
    return output, meta

def ActivationPatch(model: nn.Module, input_ids: torch.Tensor, component_ids: List[str], **kwargs) -> Tuple[Any, Dict[str, str]]:
    hooks = []
    meta = {}
    module_mapping = kwargs.get('module_mapping', {})
    source_activations = kwargs.get('source_activations', {}) # dict of component_id -> tensor
    
    def get_patch_hook(cid, src_tensor):
        def hook_fn(mod, inputs, outputs):
            if isinstance(outputs, tuple):
                return (src_tensor.clone(),) + outputs[1:]
            return src_tensor.clone()
        return hook_fn

    for cid in component_ids:
        path = module_mapping.get(cid, cid)
        src_t = source_activations[cid]
        hooks.append((path, get_patch_hook(cid, src_t)))
        meta[cid] = 'intervened'

    with apply_hooks(model, hooks):
        with torch.no_grad():
            output = model(input_ids)
            
    return output, meta
