"""Read-only adapter for the pinned official TAMAS dataset."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

ATTACK_TYPES = ("Byzantine", "Colluding", "Contradicting", "DPI", "Impersonation", "IPI")


@dataclass(frozen=True)
class TAMASCase:
    """One native TAMAS adversarial instance with source identity."""

    case_id: str
    attack_type: str
    scenario: str
    payload: dict[str, object]
    evaluation_origin: str = "tamas_official_adapter"


def load_tamas_cases(data_root: Path) -> list[TAMASCase]:
    """Load official JSON records without changing framework or evaluator semantics."""
    cases: list[TAMASCase] = []
    for attack_type in ATTACK_TYPES:
        directory = data_root / attack_type
        for path in sorted(directory.glob("*.json")):
            rows = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(rows, list):
                raise ValueError(f"TAMAS file must contain a list: {path}")
            for index, row in enumerate(rows):
                if not isinstance(row, dict) or "agents" not in row or "user query" not in row:
                    raise ValueError(f"invalid TAMAS record: {path}:{index}")
                cases.append(TAMASCase(f"{attack_type}:{path.stem}:{index:03d}", attack_type, path.stem.split("_")[0], row))
    return cases
