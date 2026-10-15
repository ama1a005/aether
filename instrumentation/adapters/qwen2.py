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
        self.intervention_applications = 0
        self.generation_hook_events: list[dict[str, int]] = []
        self._active_generation_step: int | None = None
        self.head_activations: dict[str, torch.Tensor] = {}

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

    def generate_uncached(self, inputs: dict[str, torch.Tensor], max_new_tokens: int) -> torch.Tensor:
        """Greedily decode with explicit steps and no KV cache for causal interventions."""
        if self.model is None:
            raise RuntimeError("load() must be called before generate_uncached()")
        generated = inputs["input_ids"].clone()
        attention_mask = inputs.get("attention_mask")
        if attention_mask is None:
            attention_mask = torch.ones_like(generated)
        self.generation_hook_events.clear()
        try:
            with torch.inference_mode():
                for step in range(max_new_tokens):
                    self._active_generation_step = step
                    output = self.model(
                        input_ids=generated,
                        attention_mask=attention_mask,
                        use_cache=False,
                    )
                    next_token = output.logits[:, -1, :].argmax(dim=-1, keepdim=True)
                    generated = torch.cat((generated, next_token), dim=1)
                    attention_mask = torch.cat(
                        (attention_mask, torch.ones_like(next_token)), dim=1
                    )
        finally:
            self._active_generation_step = None
        return generated

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

    def install_zero_intervention_at_positions(
        self, site: ComponentSite, token_positions: Sequence[int]
    ) -> None:
        """Zero a selected module output only at explicitly aligned token positions."""
        if self._handles:
            raise RuntimeError("remove existing hooks before installing an intervention")
        positions = tuple(token_positions)
        if not positions:
            raise ValueError("at least one token position is required")
        self.intervention_applications = 0

        def zero_positions(_module: torch.nn.Module, _inputs: tuple[Any, ...], output: Any) -> Any:
            tensor = output[0] if isinstance(output, tuple) else output
            if max(positions) >= tensor.shape[1] or min(positions) < 0:
                return None
            patched = tensor.clone()
            patched[:, positions, :] = 0
            self.intervention_applications += 1
            if isinstance(output, tuple):
                return (patched, *output[1:])
            return patched

        self._handles.append(self._module_for(site).register_forward_hook(zero_positions))

    def install_activation_patch(
        self,
        site: ComponentSite,
        source: torch.Tensor,
        token_positions: Sequence[int],
    ) -> None:
        """Patch paired source activations at aligned positions during matching sequence steps."""
        if self._handles:
            raise RuntimeError("remove existing hooks before installing an intervention")
        if source.ndim != 3:
            raise ValueError("source activation must have shape [batch, sequence, hidden]")
        positions = tuple(token_positions)
        if not positions:
            raise ValueError("at least one token position is required")
        self.intervention_applications = 0

        def patch_output(_module: torch.nn.Module, _inputs: tuple[Any, ...], output: Any) -> Any:
            tensor = output[0] if isinstance(output, tuple) else output
            if tensor.shape != source.shape:
                return None
            patched = tensor.clone()
            aligned_source = source.to(device=tensor.device, dtype=tensor.dtype)
            patched[:, positions, :] = aligned_source[:, positions, :]
            self.intervention_applications += 1
            if isinstance(output, tuple):
                return (patched, *output[1:])
            return patched

        self._handles.append(self._module_for(site).register_forward_hook(patch_output))

    def install_generation_step_patch(
        self,
        site: ComponentSite,
        source: torch.Tensor,
        target_step: int,
    ) -> None:
        """Patch the last-token state only while predicting one generated token."""
        if self._handles:
            raise RuntimeError("remove existing hooks before installing an intervention")
        if source.ndim not in (2, 3):
            raise ValueError("source must have shape [batch, hidden] or [batch, sequence, hidden]")
        if target_step < 0:
            raise ValueError("target generation step must be non-negative")
        self.intervention_applications = 0

        def patch_step(_module: torch.nn.Module, _inputs: tuple[Any, ...], output: Any) -> Any:
            tensor = output[0] if isinstance(output, tuple) else output
            step = self._active_generation_step
            if step != target_step:
                return None
            aligned = source[:, -1, :] if source.ndim == 3 else source
            if aligned.shape != tensor[:, -1, :].shape:
                raise ValueError("generation-step source shape does not match target")
            patched = tensor.clone()
            patched[:, -1, :] = aligned.to(device=tensor.device, dtype=tensor.dtype)
            self.intervention_applications += 1
            self.generation_hook_events.append({"step": step, "sequence_length": tensor.shape[1]})
            if isinstance(output, tuple):
                return (patched, *output[1:])
            return patched

        self._handles.append(self._module_for(site).register_forward_hook(patch_step))

    def _head_shape(self, layer: int) -> tuple[int, int]:
        attention = self.model.model.layers[layer].self_attn
        heads = int(attention.config.num_attention_heads)
        head_dim = int(attention.head_dim)
        if heads * head_dim != attention.o_proj.in_features:
            raise ValueError("Qwen attention head dimensions do not reconstruct o_proj input")
        return heads, head_dim

    def install_head_capture(self, layer: int) -> None:
        """Capture the exact concatenated per-head tensor entering attention o_proj."""
        if self._handles:
            raise RuntimeError("remove existing hooks before installing head capture")
        heads, head_dim = self._head_shape(layer)
        self.head_activations.clear()
        o_proj = self.model.model.layers[layer].self_attn.o_proj

        def capture(_module: torch.nn.Module, inputs: tuple[Any, ...]) -> None:
            concatenated = inputs[0]
            self.head_activations[f"L{layer}.pre_o_proj_concat"] = concatenated.detach().cpu().clone()
            self.head_activations[f"L{layer}.pre_o_proj_heads"] = (
                concatenated.view(*concatenated.shape[:-1], heads, head_dim)
                .detach().cpu().clone()
            )
            return None

        self._handles.append(o_proj.register_forward_pre_hook(capture))

    def install_head_patch(
        self,
        layer: int,
        head: int,
        source: torch.Tensor,
        token_position: int = -1,
        target_generation_step: int | None = None,
    ) -> None:
        """Patch one pre-o_proj query-head slice at one token and optional decode step."""
        if self._handles:
            raise RuntimeError("remove existing hooks before installing a head intervention")
        heads, head_dim = self._head_shape(layer)
        if head < 0 or head >= heads:
            raise IndexError(f"head {head} outside range 0..{heads - 1}")
        if source.ndim not in (2, 3):
            raise ValueError("head source must have shape [batch, head_dim] or [batch, sequence, head_dim]")
        self.intervention_applications = 0
        o_proj = self.model.model.layers[layer].self_attn.o_proj

        def patch(_module: torch.nn.Module, inputs: tuple[Any, ...]) -> tuple[Any, ...] | None:
            if target_generation_step is not None and self._active_generation_step != target_generation_step:
                return None
            concatenated = inputs[0]
            resolved = token_position if token_position >= 0 else concatenated.shape[1] + token_position
            if resolved < 0 or resolved >= concatenated.shape[1]:
                return None
            head_view = concatenated.view(*concatenated.shape[:-1], heads, head_dim).clone()
            aligned = source[:, resolved, :] if source.ndim == 3 else source
            if aligned.shape != head_view[:, resolved, head, :].shape:
                raise ValueError("head source shape does not match target")
            head_view[:, resolved, head, :] = aligned.to(concatenated.device, concatenated.dtype)
            self.intervention_applications += 1
            if self._active_generation_step is not None:
                self.generation_hook_events.append(
                    {"step": self._active_generation_step, "sequence_length": concatenated.shape[1]}
                )
            return (head_view.reshape_as(concatenated), *inputs[1:])

        self._handles.append(o_proj.register_forward_pre_hook(patch))
