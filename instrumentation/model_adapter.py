"""Architecture-neutral interfaces for local white-box language models."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import torch


@dataclass(frozen=True)
class ComponentSite:
    """One precisely named model component available for capture."""

    component_id: str
    layer: int
    component_type: str
    tensor_semantics: str


@dataclass(frozen=True)
class ActivationArtifact:
    """Metadata describing one persisted activation tensor."""

    model_id: str
    model_revision: str
    run_id: str
    component_id: str
    layer: int
    component_type: str
    token_positions: tuple[int, ...]
    tensor_shape: tuple[int, ...]
    dtype: str
    artifact_location: Path
    artifact_hash: str


class ModelAdapter(ABC):
    """Hide architecture-specific model details from causal analysis code."""

    @abstractmethod
    def load(self) -> None:
        """Load the pinned model and tokenizer."""

    @abstractmethod
    def tokenize(self, prompts: Sequence[str]) -> dict[str, torch.Tensor]:
        """Tokenize prompts into model inputs."""

    @abstractmethod
    def forward(self, inputs: dict[str, torch.Tensor]) -> Any:
        """Run a deterministic forward pass."""

    @abstractmethod
    def generate(self, inputs: dict[str, torch.Tensor], max_new_tokens: int) -> torch.Tensor:
        """Run deterministic greedy generation."""

    @abstractmethod
    def identify_components(self, layers: Sequence[int]) -> list[ComponentSite]:
        """Return capture sites with accurate tensor semantics."""

    @abstractmethod
    def install_capture_hooks(self, sites: Sequence[ComponentSite]) -> None:
        """Install read-only hooks that never replace model outputs."""

    @abstractmethod
    def remove_hooks(self) -> None:
        """Remove every installed capture or intervention hook."""
