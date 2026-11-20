"""Version-pinned semantic compatibility for BFCL 2026.3.23."""

from __future__ import annotations

from typing import Sequence


SEMANTIC_TO_OFFICIAL_CATEGORY = {
    "simple": "simple_python",
    "multiple": "multiple",
    "parallel": "parallel",
    "irrelevance": "irrelevance",
}


def official_categories(categories: Sequence[str]) -> tuple[str, ...]:
    """Translate frozen AETHER labels into exact BFCL 2026.3.23 CLI labels."""
    unknown = [item for item in categories if item not in SEMANTIC_TO_OFFICIAL_CATEGORY]
    if unknown:
        raise ValueError(f"No reviewed BFCL 2026.3.23 category mapping for: {unknown}")
    translated = tuple(SEMANTIC_TO_OFFICIAL_CATEGORY[item] for item in categories)
    if len(set(translated)) != len(translated):
        raise ValueError("BFCL category mapping is not one-to-one")
    return translated
