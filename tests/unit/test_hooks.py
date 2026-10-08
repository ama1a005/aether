import torch
import torch.nn as nn
from instrumentation.hooks.hook_registry import HookRegistry
from causal.interventions.operators import ZeroAblation, MeanAblation, ActivationPatch

class SimpleModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.l1 = nn.Linear(10, 10)
        self.l2 = nn.Linear(10, 10)
    def forward(self, x):
        return self.l2(self.l1(x))

def test_hook_noninterference():
    model = SimpleModel()
    registry = HookRegistry(model)
    x = torch.randn(1, 10)
    
    with torch.no_grad():
        out1 = model(x)
        
    registry.register('l1', 'l1')
    
    with torch.no_grad():
        out2 = model(x)
        
    assert torch.allclose(out1, out2)

def test_activation_captured():
    model = SimpleModel()
    registry = HookRegistry(model)
    registry.register('l1', 'l1')
    x = torch.randn(1, 10)
    
    with torch.no_grad():
        model(x)
        
    acts = registry.get_activations()
    assert 'l1' in acts
    assert acts['l1'].shape == (1, 10)

def test_zero_ablation_locality():
    model = SimpleModel()
    x = torch.randn(1, 10)
    out, meta = ZeroAblation(model, x, ['l1'])
    assert meta['l1'] == 'intervened'

def test_mean_ablation():
    model = SimpleModel()
    x = torch.randn(1, 10)
    out, meta = MeanAblation(model, x, ['l1'], means={'l1': torch.zeros(1, 10)})
    assert meta['l1'] == 'intervened'

def test_activation_patch():
    model = SimpleModel()
    x = torch.randn(1, 10)
    out, meta = ActivationPatch(model, x, ['l1'], source_activations={'l1': torch.ones(1, 10)})
    assert meta['l1'] == 'intervened'
