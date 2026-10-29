"""Staged mediator replay with explicitly declared off-path output freezes.

The caller must supply a valid causal cut for its architecture. This implements
node-mediated path isolation under that cut, not arbitrary neural edge patching.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import torch
from torch import nn

from causal.interventions.advanced import InterventionTarget, execute_path_patch, _resolve_module


@dataclass(frozen=True)
class PathReplayResult:
    """Raw outputs and intervention records for the three replay stages."""

    baseline_output: object
    source_patched_output: object
    isolated_output: object
    propagated_mediator: torch.Tensor
    stage_records: tuple


def replay_mediated_path(model: nn.Module, inputs: torch.Tensor,
                         source: InterventionTarget, mediator: InterventionTarget,
                         source_activation: torch.Tensor,
                         off_path: tuple[InterventionTarget, ...]) -> PathReplayResult:
    """Capture baseline, propagate source through a cut, then replay mediator.

Only evaluation-mode, single-invocation residual-output sites are supported.
All declared off-path sites are restored to baseline in both intervention runs.
Each forward pass uses the same input. No ground-truth labels are consulted.
"""
    targets = (source, mediator, *off_path)
    if model.training:
        raise ValueError("Path replay requires model.eval()")
    if any(t.operator != "residual_patch" for t in targets):
        raise ValueError("Path replay currently requires residual-output sites")
    if len({t.module_path for t in targets}) != len(targets):
        raise ValueError("Source, mediator and off-path sites must be distinct")
    if len({t.component_id for t in targets}) != len(targets):
        raise ValueError("Path component identities must be distinct")

    def capture(run: Callable[[], object], sites: tuple[InterventionTarget, ...]):
        handles = []
        captured = {}
        order = []

        def hook_for(site):
            def hook(_module, _inputs, output):
                if site.component_id in captured:
                    raise ValueError("Repeated module execution requires call-index addressing")
                tensor = output[0] if isinstance(output, tuple) else output
                if not isinstance(tensor, torch.Tensor):
                    raise TypeError("Path site must produce a tensor")
                captured[site.component_id] = tensor.detach().clone()
                order.append(site.component_id)
            return hook

        try:
            for site in sites:
                handles.append(_resolve_module(model, site.module_path).register_forward_hook(hook_for(site)))
            with torch.no_grad():
                result = run()
            if set(captured) != {site.component_id for site in sites}:
                raise RuntimeError("Path sites did not all execute")
            return result, captured, order
        finally:
            for handle in handles:
                handle.remove()

    baseline, baseline_cache, order = capture(lambda: model(inputs), targets)
    if order.index(source.component_id) >= order.index(mediator.component_id):
        raise ValueError("Source must execute before mediator")
    freezes = {site.component_id: baseline_cache[site.component_id] for site in off_path}
    (propagated_output, propagation_records), propagated, _ = capture(
        lambda: execute_path_patch(model, inputs, (source, *off_path),
                                   {source.component_id: source_activation, **freezes}),
        (mediator,))
    isolated, replay_records = execute_path_patch(
        model, inputs, (mediator, *off_path),
        {mediator.component_id: propagated[mediator.component_id], **freezes})
    return PathReplayResult(baseline, propagated_output, isolated,
                            propagated[mediator.component_id],
                            (propagation_records, replay_records))
