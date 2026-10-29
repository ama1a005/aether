"""Strict tensor-selective intervention operators for Phase 1 experiments."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Callable, Iterator, Protocol, Sequence

import torch
from torch import nn


class SAECodec(Protocol):
    """Minimal sparse-autoencoder interface used by feature patching."""

    def encode(self, activation: torch.Tensor) -> torch.Tensor:
        """Map model activations to latent features."""

    def decode(self, features: torch.Tensor) -> torch.Tensor:
        """Map latent features back to model activations."""


@dataclass(frozen=True)
class InterventionTarget:
    """One fully addressed intervention site and its source provenance."""

    component_id: str
    module_path: str
    token_positions: tuple[int, ...]
    source_run: str
    operator: str = "residual_patch"
    head_indices: tuple[int, ...] = ()
    feature_indices: tuple[int, ...] = ()
    num_heads: int | None = None

    def __post_init__(self) -> None:
        if not self.component_id or not self.module_path or not self.source_run:
            raise ValueError("Component, module path, and source run are required")
        if self.operator not in {"residual_patch", "head_output_patch", "sae_feature_patch"}:
            raise ValueError("Unknown advanced intervention operator")
        _validate_indices("token", self.token_positions, required=True)
        _validate_indices("head", self.head_indices, required=self.operator == "head_output_patch")
        _validate_indices("feature", self.feature_indices, required=self.operator == "sae_feature_patch")
        if self.operator == "head_output_patch" and (type(self.num_heads) is not int or self.num_heads < 1):
            raise ValueError("Head patching requires a positive num_heads")
        if self.operator != "head_output_patch" and self.num_heads is not None:
            raise ValueError("num_heads applies only to head output patching")


@dataclass(frozen=True)
class InterventionRecord:
    """Auditable metadata for one applied tensor intervention."""

    component_id: str
    module_path: str
    operator: str
    token_positions: tuple[int, ...]
    head_indices: tuple[int, ...]
    feature_indices: tuple[int, ...]
    source_run: str
    tensor_shape: tuple[int, ...]
    dtype: str
    device: str


def _validate_indices(name: str, values: tuple[int, ...], *, required: bool) -> None:
    if required and not values:
        raise ValueError(f"{name} indices are required")
    if any(type(value) is not int or value < 0 for value in values) or len(set(values)) != len(values):
        raise ValueError(f"{name} indices must be unique nonnegative integers")


def _validate_pair(destination: torch.Tensor, source: torch.Tensor) -> None:
    if not isinstance(destination, torch.Tensor) or not isinstance(source, torch.Tensor):
        raise TypeError("Source and destination must be tensors")
    if destination.shape != source.shape:
        raise ValueError("Source and destination activation shapes differ")
    if destination.dtype != source.dtype or destination.device != source.device:
        raise ValueError("Source and destination dtype/device must match exactly")
    if destination.ndim < 3:
        raise ValueError("Interventions require [batch, tokens, hidden...] activations")
    if not destination.is_floating_point() or not torch.isfinite(destination).all() or not torch.isfinite(source).all():
        raise ValueError("Activations must be finite floating-point tensors")


def _validate_bounds(values: Sequence[int], limit: int, name: str) -> None:
    _validate_indices(name, tuple(values), required=True)
    if any(value >= limit for value in values):
        raise IndexError(f"{name} index exceeds activation bounds")


def residual_stream_patch(destination: torch.Tensor, source: torch.Tensor,
                          token_positions: Sequence[int]) -> torch.Tensor:
    """Patch complete hidden vectors at explicitly selected token positions."""
    _validate_pair(destination, source)
    _validate_bounds(token_positions, destination.shape[1], "token")
    patched = destination.clone()
    patched[:, list(token_positions), ...] = source[:, list(token_positions), ...]
    return patched


def head_output_patch(destination: torch.Tensor, source: torch.Tensor, token_positions: Sequence[int],
                      head_indices: Sequence[int], num_heads: int) -> torch.Tensor:
    """Patch selected concatenated attention-head outputs at selected tokens."""
    _validate_pair(destination, source)
    _validate_bounds(token_positions, destination.shape[1], "token")
    if type(num_heads) is not int or num_heads < 1 or destination.ndim != 3:
        raise ValueError("Head patch requires positive num_heads and [batch, tokens, hidden]")
    if destination.shape[-1] % num_heads:
        raise ValueError("Hidden dimension is not divisible by num_heads")
    _validate_bounds(head_indices, num_heads, "head")
    shape = (*destination.shape[:-1], num_heads, destination.shape[-1] // num_heads)
    patched = destination.clone().reshape(shape)
    source_heads = source.reshape(shape)
    for token_position in token_positions:
        for head_index in head_indices:
            patched[:, token_position, head_index, :] = source_heads[:, token_position, head_index, :]
    return patched.reshape_as(destination)


def sae_feature_patch(destination: torch.Tensor, source: torch.Tensor, token_positions: Sequence[int],
                      feature_indices: Sequence[int], codec: SAECodec) -> torch.Tensor:
    """Replace selected SAE latents and decode only the selected token vectors."""
    _validate_pair(destination, source)
    _validate_bounds(token_positions, destination.shape[1], "token")
    destination_tokens = destination[:, list(token_positions), ...]
    source_tokens = source[:, list(token_positions), ...]
    destination_features = codec.encode(destination_tokens)
    source_features = codec.encode(source_tokens)
    _validate_pair(destination_features, source_features)
    if destination_features.shape[:-1] != destination_tokens.shape[:-1]:
        raise ValueError("SAE codec returned incompatible feature tensors")
    _validate_bounds(feature_indices, destination_features.shape[-1], "feature")
    patched_features = destination_features.clone()
    patched_features[..., list(feature_indices)] = source_features[..., list(feature_indices)]
    decoded = codec.decode(patched_features)
    reconstructed = codec.decode(destination_features)
    _validate_pair(destination_tokens, decoded)
    _validate_pair(destination_tokens, reconstructed)
    patched = destination.clone()
    # Keep the original reconstruction residual: only the selected latent delta
    # should change behavior, not an unrelated autoencoder reconstruction error.
    patched[:, list(token_positions), ...] = destination_tokens + (decoded - reconstructed)
    return patched


def _resolve_module(model: nn.Module, path: str) -> nn.Module:
    current: nn.Module = model
    for part in path.split("."):
        if part.isdigit() and isinstance(current, (nn.ModuleList, nn.Sequential)):
            current = current[int(part)]
        else:
            candidate = getattr(current, part, None)
            if not isinstance(candidate, nn.Module):
                raise ValueError(f"Module path does not resolve: {path}")
            current = candidate
    return current


@contextmanager
def intervention_hooks(model: nn.Module, targets: Sequence[InterventionTarget],
                       source_activations: dict[str, torch.Tensor],
                       sae_codecs: dict[str, SAECodec] | None = None) -> Iterator[list[InterventionRecord]]:
    """Install a multi-site path patch and always remove every registered hook."""
    if not targets or len({target.component_id for target in targets}) != len(targets):
        raise ValueError("Path patch targets must be nonempty and component-unique")
    if len({target.module_path for target in targets}) != len(targets):
        raise ValueError("Duplicate module targets require an explicit composition operator")
    missing = {target.component_id for target in targets} - source_activations.keys()
    if missing:
        raise ValueError(f"Missing source activations: {sorted(missing)}")
    codecs = sae_codecs or {}
    handles: list[torch.utils.hooks.RemovableHandle] = []
    records: list[InterventionRecord] = []

    def make_hook(target: InterventionTarget) -> Callable:
        source = source_activations[target.component_id]

        def hook(_module: nn.Module, _inputs: tuple, output: object) -> object:
            tensor = output[0] if isinstance(output, tuple) else output
            if not isinstance(tensor, torch.Tensor):
                raise TypeError("Intervention target output must be a tensor or tensor-first tuple")
            if target.operator == "residual_patch":
                patched = residual_stream_patch(tensor, source, target.token_positions)
            elif target.operator == "head_output_patch":
                patched = head_output_patch(tensor, source, target.token_positions,
                                            target.head_indices, target.num_heads or 0)
            else:
                if target.component_id not in codecs:
                    raise ValueError(f"Missing SAE codec for {target.component_id}")
                patched = sae_feature_patch(tensor, source, target.token_positions,
                                            target.feature_indices, codecs[target.component_id])
            records.append(InterventionRecord(target.component_id, target.module_path, target.operator,
                           target.token_positions, target.head_indices, target.feature_indices,
                           target.source_run, tuple(tensor.shape), str(tensor.dtype), str(tensor.device)))
            return (patched, *output[1:]) if isinstance(output, tuple) else patched
        return hook

    try:
        for target in targets:
            handles.append(_resolve_module(model, target.module_path).register_forward_hook(make_hook(target)))
        yield records
        missing_firings = {target.component_id for target in targets} - {r.component_id for r in records}
        if missing_firings:
            raise RuntimeError(f"Intervention targets did not execute: {sorted(missing_firings)}")
    finally:
        for handle in handles:
            handle.remove()


def execute_path_patch(model: nn.Module, inputs: torch.Tensor, targets: Sequence[InterventionTarget],
                       source_activations: dict[str, torch.Tensor],
                       sae_codecs: dict[str, SAECodec] | None = None) -> tuple[object, tuple[InterventionRecord, ...]]:
    """Execute simultaneous node patches; this alone does not isolate a path."""
    with intervention_hooks(model, targets, source_activations, sae_codecs) as records:
        with torch.no_grad():
            output = model(inputs)
    return output, tuple(records)
