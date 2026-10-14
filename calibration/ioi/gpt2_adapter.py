"""GPT-2 head-output capture and patching behind an architecture adapter."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

import torch

from instrumentation.model_adapter import ComponentSite, ModelAdapter


Head = tuple[int, int]


class GPT2IOIAdapter(ModelAdapter):
    """Pinned local GPT-2 adapter exposing pre-projection per-head outputs."""

    def __init__(self, model_path: Path, revision: str, device: str = "cpu") -> None:
        self.model_path = model_path
        self.revision = revision
        self.device = device
        self.model: Any = None
        self.tokenizer: Any = None
        self._handles: list[Any] = []
        self.activations: dict[str, torch.Tensor] = {}

    def load(self) -> None:
        """Load the pinned local model without remote code."""
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_path, local_files_only=True, trust_remote_code=False
        )
        self.tokenizer.pad_token = self.tokenizer.eos_token
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_path, local_files_only=True, trust_remote_code=False, dtype=torch.float32
        ).to(self.device)
        self.model.eval()

    def tokenize(self, prompts: list[str]) -> dict[str, torch.Tensor]:
        """Tokenize equal-length prompts without adding special tokens."""
        encoded = self.tokenizer(prompts, return_tensors="pt", padding=False, add_special_tokens=False)
        return {key: value.to(self.device) for key, value in encoded.items()}

    def forward(self, inputs: dict[str, torch.Tensor]) -> Any:
        """Run deterministic inference."""
        with torch.inference_mode():
            return self.model(**inputs)

    def generate(self, inputs: dict[str, torch.Tensor], max_new_tokens: int) -> torch.Tensor:
        """Generate greedily."""
        with torch.inference_mode():
            return self.model.generate(**inputs, do_sample=False, max_new_tokens=max_new_tokens)

    def identify_components(self, layers: list[int]) -> list[ComponentSite]:
        """Identify each head output immediately before the attention output projection."""
        sites: list[ComponentSite] = []
        for layer in layers:
            for head in range(self.model.config.n_head):
                sites.append(
                    ComponentSite(
                        f"L{layer}.H{head}.z",
                        layer,
                        "attention_head_output",
                        "per-head attention output z before c_proj",
                    )
                )
        return sites

    def install_capture_hooks(self, sites: list[ComponentSite]) -> None:
        """Install read-only pre-hooks on attention output projections."""
        if self._handles:
            raise RuntimeError("hooks already installed")
        self.activations.clear()
        by_layer: dict[int, list[int]] = {}
        for site in sites:
            head = int(site.component_id.split(".H")[1].split(".")[0])
            by_layer.setdefault(site.layer, []).append(head)
        head_dim = self.model.config.n_embd // self.model.config.n_head
        for layer, heads in by_layer.items():
            def capture(_module: torch.nn.Module, args: tuple[Any, ...], *, layer: int = layer, heads: list[int] = heads) -> None:
                merged = args[0]
                for head in heads:
                    start = head * head_dim
                    self.activations[f"L{layer}.H{head}.z"] = merged[..., start:start + head_dim].detach().cpu().clone()
                return None

            module = self.model.transformer.h[layer].attn.c_proj
            self._handles.append(module.register_forward_pre_hook(capture))

    def install_head_patch_hooks(
        self, heads: Iterable[Head], clean_activations: dict[str, torch.Tensor], position: int = -1
    ) -> None:
        """Patch selected corrupted head outputs with paired clean outputs at one position."""
        if self._handles:
            raise RuntimeError("hooks already installed")
        by_layer: dict[int, list[int]] = {}
        for layer, head in heads:
            by_layer.setdefault(layer, []).append(head)
        head_dim = self.model.config.n_embd // self.model.config.n_head
        for layer, layer_heads in by_layer.items():
            def patch(_module: torch.nn.Module, args: tuple[Any, ...], *, layer: int = layer, layer_heads: list[int] = layer_heads) -> tuple[Any, ...]:
                merged = args[0].clone()
                for head in layer_heads:
                    start = head * head_dim
                    source = clean_activations[f"L{layer}.H{head}.z"].to(merged.device)
                    merged[:, position, start:start + head_dim] = source[:, position, :]
                return (merged, *args[1:])

            module = self.model.transformer.h[layer].attn.c_proj
            self._handles.append(module.register_forward_pre_hook(patch))

    def remove_hooks(self) -> None:
        """Remove all hooks idempotently."""
        for handle in self._handles:
            handle.remove()
        self._handles.clear()
