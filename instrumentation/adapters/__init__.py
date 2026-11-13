"""Architecture-specific model adapters."""

from .qwen2 import HeadPatch, ModulePatch, Qwen2ModelAdapter

__all__ = ["HeadPatch", "ModulePatch", "Qwen2ModelAdapter"]
