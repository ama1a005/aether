"""Qwen2-family adapter with selected, read-only activation capture."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

import torch

from instrumentation.model_adapter import ComponentSite, ModelAdapter


class Qwen2ModelAdapter(ModelAdapter):
    """Adapter for pinned local Qwen2/Qwen2.5 causal language models."""

    def __init__(
        self,
        model_id: str,
        revision: str,
        cache_dir: Path,
        dtype: torch.dtype = torch.float32,
        device: str = "cpu",
        local_files_only: bool = False,
    ) -> None:
        self.model_id = model_id
        self.revision = revision
        self.cache_dir = cache_dir
        self.dtype = dtype
        self.device = device
        self.local_files_only = local_files_only
        self.model: Any = None
        self.tokenizer: Any = None
        self.activations: dict[str, torch.Tensor] = {}
        self._handles: list[Any] = []

    def load(self) -> None:
        """Load the exact requested revision without remote model code."""
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_id,
            revision=self.revision,
            cache_dir=self.cache_dir,
            local_files_only=self.local_files_only,
            trust_remote_code=False,
        )
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_id,
            revision=self.revision,
            cache_dir=self.cache_dir,
            local_files_only=self.local_files_only,
            trust_remote_code=False,
            dtype=self.dtype,
            attn_implementation="eager",
        ).to(self.device)
        self.model.eval()

    def tokenize(self, prompts: Sequence[str]) -> dict[str, torch.Tensor]:
        """Tokenize raw prompts with padding and move tensors to the device."""
        if self.tokenizer is None:
            raise RuntimeError("load() must be called before tokenize()")
        encoded = self.tokenizer(list(prompts), return_tensors="pt", padding=True)
        return {name: tensor.to(self.device) for name, tensor in encoded.items()}

    def forward(self, inputs: dict[str, torch.Tensor]) -> Any:
        """Run a no-gradient deterministic forward pass."""
        if self.model is None:
            raise RuntimeError("load() must be called before forward()")
        with torch.inference_mode():
            return self.model(**inputs)

    def generate(self, inputs: dict[str, torch.Tensor], max_new_tokens: int) -> torch.Tensor:
        """Generate greedily with sampling disabled."""
        if self.model is None:
            raise RuntimeError("load() must be called before generate()")
        with torch.inference_mode():
            return self.model.generate(**inputs, do_sample=False, max_new_tokens=max_new_tokens)

    def identify_components(self, layers: Sequence[int]) -> list[ComponentSite]:
        """Expose block, post-attention projection, and MLP outputs at selected layers."""
        if self.model is None:
            raise RuntimeError("load() must be called before identify_components()")
        layer_count = len(self.model.model.layers)
        sites: list[ComponentSite] = []
        for layer in layers:
            if layer < 0 or layer >= layer_count:
                raise IndexError(f"layer {layer} outside model range 0..{layer_count - 1}")
            sites.extend(
                [
                    ComponentSite(f"L{layer}.block_output", layer, "block_output", "decoder block output residual stream"),
                    ComponentSite(f"L{layer}.attention_output", layer, "attention_output", "self-attention module output before residual addition"),
                    ComponentSite(f"L{layer}.mlp_output", layer, "mlp_output", "MLP module output before residual addition"),
                ]
            )
        return sites

    def _module_for(self, site: ComponentSite) -> torch.nn.Module:
        layer = self.model.model.layers[site.layer]
        return {
            "block_output": layer,
            "attention_output": layer.self_attn,
            "mlp_output": layer.mlp,
        }[site.component_type]

    def install_capture_hooks(self, sites: Sequence[ComponentSite]) -> None:
        """Install passive hooks; callbacks intentionally return ``None``."""
        if self._handles:
            raise RuntimeError("capture hooks are already installed")
        self.activations.clear()
        for site in sites:
            def capture(_module: torch.nn.Module, _inputs: tuple[Any, ...], output: Any, *, component_id: str = site.component_id) -> None:
                tensor = output[0] if isinstance(output, tuple) else output
                self.activations[component_id] = tensor.detach().cpu().clone()
                return None

            self._handles.append(self._module_for(site).register_forward_hook(capture))

    def remove_hooks(self) -> None:
        """Remove hooks idempotently and prevent accumulation between runs."""
        for handle in self._handles:
            handle.remove()
        self._handles.clear()

    def install_zero_intervention(self, site: ComponentSite) -> None:
        """Install one active hook that zeros exactly the selected module output."""
        if self._handles:
            raise RuntimeError("remove existing hooks before installing an intervention")

        def zero_output(_module: torch.nn.Module, _inputs: tuple[Any, ...], output: Any) -> Any:
            if isinstance(output, tuple):
                return (torch.zeros_like(output[0]), *output[1:])
            return torch.zeros_like(output)

        self._handles.append(self._module_for(site).register_forward_hook(zero_output))
