"""Architecture-specific model adapters."""

from .qwen2 import HeadPatch, ModulePatch, Qwen2ModelAdapter
from .llama import LlamaModelAdapter

__all__ = ["HeadPatch", "LlamaModelAdapter", "ModulePatch", "Qwen2ModelAdapter"]
