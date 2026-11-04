"""Staged path replay with call-index addressing and explicit causal cuts."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

import torch
from torch import nn

from causal.interventions.advanced import InterventionTarget, _resolve_module, residual_stream_patch


@dataclass(frozen=True)
class ReplaySite:
    """One residual-output site, disambiguated by zero-based invocation index."""
    target: InterventionTarget
    call_index: int = 0

    def __post_init__(self) -> None:
        if self.target.operator != "residual_patch":
            raise ValueError("Path replay sites must use residual_patch")
        if type(self.call_index) is not int or self.call_index < 0:
            raise ValueError("call_index must be a nonnegative integer")

    @property
    def key(self) -> str:
        """Return a stable identity for one module invocation."""
        return f"{self.target.component_id}@{self.call_index}"


@dataclass(frozen=True)
class PathStage:
    """One propagation stage and the mediator activation it produced."""
    patched_site: str
    captured_site: str
    activation: torch.Tensor
    output: object


@dataclass(frozen=True)
class GeneralPathReplayResult:
    """Complete outputs and activations for an ordered path replay."""
    baseline_output: object
    isolated_output: object
    stages: tuple[PathStage, ...]
    baseline_activations: dict[str, torch.Tensor]
    execution_order: tuple[str, ...]


@dataclass(frozen=True)
class PathReplayResult:
    """Compatibility result for the original one-mediator API."""
    baseline_output: object
    source_patched_output: object
    isolated_output: object
    propagated_mediator: torch.Tensor
    stage_records: tuple


def _tensor(output: object) -> torch.Tensor:
    value = output[0] if isinstance(output, tuple) else output
    if not isinstance(value, torch.Tensor):
        raise TypeError("Path site must produce a tensor or tensor-first tuple")
    return value


def _replace(output: object, value: torch.Tensor) -> object:
    return (value, *output[1:]) if isinstance(output, tuple) else value


def _run_with_sites(model: nn.Module, inputs: torch.Tensor, sites: Sequence[ReplaySite],
                    patches: dict[str, torch.Tensor] | None = None,
                    capture_keys: frozenset[str] | None = None,
                    ) -> tuple[object, dict[str, torch.Tensor], tuple[str, ...]]:
    """Execute one pass, patching and capturing addressed module invocations."""
    if len({site.key for site in sites}) != len(sites):
        raise ValueError("Replay site identities and call indices must be unique")
    patch_values = patches or {}
    unknown = set(patch_values) - {site.key for site in sites}
    if unknown:
        raise ValueError(f"Patch keys are not declared replay sites: {sorted(unknown)}")
    wanted = capture_keys if capture_keys is not None else frozenset(site.key for site in sites)
    counters: dict[str, int] = {}
    captures: dict[str, torch.Tensor] = {}
    order: list[str] = []
    handles = []
    by_module: dict[str, list[ReplaySite]] = {}
    for site in sites:
        by_module.setdefault(site.target.module_path, []).append(site)

    def hook_for(path: str, addressed: list[ReplaySite]) -> Callable:
        lookup = {site.call_index: site for site in addressed}

        def hook(_module: nn.Module, _args: tuple, output: object) -> object:
            index = counters.get(path, 0)
            counters[path] = index + 1
            site = lookup.get(index)
            if site is None:
                return output
            tensor = _tensor(output)
            if not tensor.is_floating_point() or not torch.isfinite(tensor).all():
                raise ValueError("Path activations must be finite floating tensors")
            if site.key in patch_values:
                tensor = residual_stream_patch(tensor, patch_values[site.key],
                                               site.target.token_positions)
                output = _replace(output, tensor)
            order.append(site.key)
            if site.key in wanted:
                captures[site.key] = tensor.detach().clone()
            return output
        return hook

    try:
        for path, addressed in by_module.items():
            handles.append(_resolve_module(model, path).register_forward_hook(hook_for(path, addressed)))
        with torch.no_grad():
            result = model(inputs)
        missing = wanted - captures.keys()
        if missing:
            raise RuntimeError(f"Addressed replay sites did not execute: {sorted(missing)}")
        return result, captures, tuple(order)
    finally:
        for handle in handles:
            handle.remove()


def replay_path(model: nn.Module, inputs: torch.Tensor, source: ReplaySite,
                mediators: Sequence[ReplaySite], source_activation: torch.Tensor,
                cuts: Sequence[ReplaySite] = ()) -> GeneralPathReplayResult:
    """Replay an ordered multi-mediator path under explicit baseline freezes.

    Each stage patches the previously propagated activation, freezes every
    declared cut, and captures the next mediator. A final pass patches the last
    mediator. The caller owns the validity and completeness of the causal cut.
    """
    if model.training:
        raise ValueError("Path replay requires model.eval()")
    if not mediators:
        raise ValueError("At least one mediator is required")
    path = (source, *mediators)
    all_sites = (*path, *cuts)
    if len({site.key for site in all_sites}) != len(all_sites):
        raise ValueError("Path and cut sites must be uniquely addressed")
    if len({site.target.component_id for site in all_sites}) != len(all_sites):
        raise ValueError("Component identities must be unique across path and cuts")
    baseline, baseline_cache, order = _run_with_sites(model, inputs, all_sites)
    positions = {key: index for index, key in enumerate(order)}
    if any(positions[left.key] >= positions[right.key] for left, right in zip(path, path[1:])):
        raise ValueError("Each source or mediator must execute before the next mediator")
    freezes = {site.key: baseline_cache[site.key] for site in cuts}
    stages: list[PathStage] = []
    upstream = source
    propagated = source_activation
    for mediator in mediators:
        output, captured, _ = _run_with_sites(
            model, inputs, all_sites, {upstream.key: propagated, **freezes},
            frozenset({mediator.key}))
        propagated = captured[mediator.key]
        stages.append(PathStage(upstream.key, mediator.key, propagated, output))
        upstream = mediator
    isolated, _, _ = _run_with_sites(model, inputs, all_sites,
                                      {upstream.key: propagated, **freezes}, frozenset())
    return GeneralPathReplayResult(baseline, isolated, tuple(stages), baseline_cache, order)


def replay_mediated_path(model: nn.Module, inputs: torch.Tensor,
                         source: InterventionTarget, mediator: InterventionTarget,
                         source_activation: torch.Tensor,
                         off_path: tuple[InterventionTarget, ...]) -> PathReplayResult:
    """Compatibility wrapper for a single mediator at call index zero."""
    result = replay_path(model, inputs, ReplaySite(source), (ReplaySite(mediator),),
                         source_activation, tuple(ReplaySite(site) for site in off_path))
    stage = result.stages[0]
    return PathReplayResult(result.baseline_output, stage.output, result.isolated_output,
                            stage.activation,
                            ({"patched": stage.patched_site, "captured": stage.captured_site},))
