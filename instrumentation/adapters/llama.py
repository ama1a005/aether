"""Adapter for Hugging Face Llama-family decoder-only language models."""

from __future__ import annotations

from instrumentation.adapters.qwen2 import Qwen2ModelAdapter


class LlamaModelAdapter(Qwen2ModelAdapter):
    """Reuse shared decoder hooks while enforcing a Llama architecture."""

    def load(self) -> None:
        """Load the pinned checkpoint and reject any non-Llama architecture."""
        super().load()
        model_type = str(getattr(self.model.config, "model_type", ""))
        if model_type != "llama":
            del self.model
            self.model = None
            raise ValueError(f"expected model_type llama, observed {model_type!r}")

