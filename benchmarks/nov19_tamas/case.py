"""Typed data models and loaders for native TAMAS dataset."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
import random
from typing import Any, Sequence

OFFICIAL_REPOSITORY = "https://github.com/microsoft/TAMAS"
OFFICIAL_COMMIT = "545c112af9aab93b7ef2b0b60831d93c81c365c3"
CODE_LICENSE = "MIT"
DATA_LICENSE = "CDLA-Permissive-2.0"
ATTACK_TYPES = (
    "Byzantine",
    "Colluding",
    "Contradicting",
    "DPI",
    "Impersonation",
    "IPI",
)
TOTAL_RECORDS = 300
PER_ATTACK_RECORDS = 50


@dataclass(frozen=True)
class TAMASNativeCase:
    """One native TAMAS adversarial case with original agent and task specification."""
    case_id: str
    attack_type: str
    scenario: str
    user_query: str
    agents: tuple[dict[str, Any], ...]
    payload: dict[str, Any]
    evaluation_origin: str = "tamas_native_official"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["agents"] = list(self.agents)
        return data


def load_tamas_dataset(data_root: Path) -> list[TAMASNativeCase]:
    """Load native TAMAS dataset files from data directory."""
    data_root = Path(data_root)
    if not data_root.is_dir():
        raise FileNotFoundError(f"TAMAS data directory not found: {data_root}")

    cases: list[TAMASNativeCase] = []
    for attack in ATTACK_TYPES:
        attack_dir = data_root / attack
        if not attack_dir.is_dir():
            raise FileNotFoundError(f"TAMAS attack directory missing: {attack_dir}")

        json_files = sorted(attack_dir.glob("*.json"))
        if not json_files:
            raise FileNotFoundError(f"No JSON records found in {attack_dir}")

        for jf in json_files:
            try:
                rows = json.loads(jf.read_text(encoding="utf-8"))
            except Exception as exc:
                raise ValueError(f"Corrupt JSON file {jf}: {exc}") from exc

            if not isinstance(rows, list):
                raise ValueError(f"TAMAS data file must contain a list: {jf}")

            scenario_name = jf.stem.split("_")[0]
            for idx, row in enumerate(rows):
                if not isinstance(row, dict):
                    raise ValueError(f"Invalid record at {jf}:{idx}")
                if "agents" not in row or "user query" not in row:
                    raise ValueError(f"Missing required fields (agents, user query) in {jf}:{idx}")

                cid = f"{attack}:{jf.stem}:{idx:03d}"
                agents = tuple(row["agents"]) if isinstance(row["agents"], list) else ()
                case = TAMASNativeCase(
                    case_id=cid,
                    attack_type=attack,
                    scenario=scenario_name,
                    user_query=str(row["user query"]),
                    agents=agents,
                    payload=dict(row),
                    evaluation_origin="tamas_native_official",
                )
                cases.append(case)

    return cases


def select_predeclared_tamas_cohort(
    cases: Sequence[TAMASNativeCase],
    per_attack_count: int | None = None,
    seed: int = 42,
) -> list[TAMASNativeCase]:
    """Select a deterministic cohort balanced across all six attack types."""
    if not cases:
        raise ValueError("Cannot select from empty cases sequence")

    by_attack: dict[str, list[TAMASNativeCase]] = {at: [] for at in ATTACK_TYPES}
    for c in sorted(cases, key=lambda c: c.case_id):
        if c.attack_type in by_attack:
            by_attack[c.attack_type].append(c)

    if per_attack_count is None:
        # Full set
        selected: list[TAMASNativeCase] = []
        for at in ATTACK_TYPES:
            selected.extend(by_attack[at])
        return sorted(selected, key=lambda c: c.case_id)

    if per_attack_count < 1:
        raise ValueError(f"per_attack_count must be positive, got {per_attack_count}")

    rng = random.Random(seed)
    selected = []
    for at in ATTACK_TYPES:
        group = by_attack[at]
        if not group:
            continue
        take = min(per_attack_count, len(group))
        # Stable deterministic selection
        selected.extend(group[:take])

    return sorted(selected, key=lambda c: c.case_id)
