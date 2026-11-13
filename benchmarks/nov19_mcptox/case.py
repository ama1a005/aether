"""Typed data structures and loaders for official MCPTox benchmark cases."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
import random
from typing import Any, Sequence

OFFICIAL_REPOSITORY = "https://github.com/zhiqiangwang4/MCPTox-Benchmark"
OFFICIAL_COMMIT = "f85189f9ad12504c197c7f920ab818a40657b1fa"
PURE_TOOL_SHA256 = "9a321dc4ecf4869883cf2a29ea8189e1f7663720a9c41a3e5ce2323d580e31c1"
RESPONSE_SHA256 = "4f8177dcbe3718ce3d6ea6a0eec8fa27813158179bd30afe340fe854e886fdf5"
TOTAL_PINNED_CASES = 485
TOTAL_PINNED_SERVERS = 45


@dataclass(frozen=True)
class MCPToxNativeCase:
    """One native MCPTox case retaining complete metadata and attack semantics."""
    case_id: str
    server_name: str
    tool_name: str
    query: str
    poisoned_description: str
    security_risk: str
    paradigm: str
    tool_address: str
    raw_metadata: dict[str, Any]
    evaluation_origin: str = "mcptox_official_compatible"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_native_cases(
    pure_tool_path: Path,
    verify_pinned_hash: bool = True,
) -> list[MCPToxNativeCase]:
    """Load official pure_tool.json preserving native 45-server 485-case structure."""
    pure_tool_path = Path(pure_tool_path)
    if not pure_tool_path.is_file():
        raise FileNotFoundError(f"MCPTox pure_tool.json not found: {pure_tool_path}")

    if verify_pinned_hash:
        digest = sha256(pure_tool_path.read_bytes()).hexdigest()
        if digest != PURE_TOOL_SHA256:
            raise ValueError(
                f"MCPTox pure_tool.json SHA256 mismatch: expected {PURE_TOOL_SHA256}, got {digest}"
            )

    payload = json.loads(pure_tool_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("MCPTox root must be a list of server dictionaries")

    cases: list[MCPToxNativeCase] = []
    required_keys = {
        "server_name", "tool_name", "query", "tool_content",
        "security risk", "paradigm", "tool_address",
    }

    for group_idx, server_group in enumerate(payload):
        if not isinstance(server_group, dict):
            raise ValueError(f"MCPTox group {group_idx} is not a dictionary")
        for case_id, row in server_group.items():
            if not isinstance(row, dict):
                raise ValueError(f"MCPTox record {case_id} is not a dictionary")
            missing = required_keys - set(row)
            if missing:
                raise ValueError(f"Record {case_id} missing required keys: {missing}")

            case = MCPToxNativeCase(
                case_id=case_id,
                server_name=str(row["server_name"]),
                tool_name=str(row["tool_name"]),
                query=str(row["query"]),
                poisoned_description=str(row["tool_content"]),
                security_risk=str(row["security risk"]),
                paradigm=str(row["paradigm"]),
                tool_address=str(row["tool_address"]),
                raw_metadata=dict(row),
                evaluation_origin="mcptox_official_compatible",
            )
            cases.append(case)

    return cases


def select_predeclared_subset(
    cases: Sequence[MCPToxNativeCase],
    count: int | None = None,
    seed: int = 42,
    stratify_by_paradigm: bool = False,
) -> list[MCPToxNativeCase]:
    """Select a deterministic subset stably sorted by case_id without outcome conditioning."""
    if not cases:
        raise ValueError("Cannot select from empty cases sequence")

    # Always sort first for determinism
    sorted_cases = sorted(cases, key=lambda c: c.case_id)
    if count is None or count >= len(sorted_cases):
        return list(sorted_cases)

    if count < 1:
        raise ValueError(f"Count must be positive, got {count}")

    if not stratify_by_paradigm:
        # Stable prefix after case_id sorting
        return sorted_cases[:count]

    # Stratified selection across paradigms
    by_paradigm: dict[str, list[MCPToxNativeCase]] = {}
    for c in sorted_cases:
        by_paradigm.setdefault(c.paradigm, []).append(c)

    selected: list[MCPToxNativeCase] = []
    paradigms = sorted(by_paradigm.keys())
    per_paradigm = count // len(paradigms)
    remainder = count % len(paradigms)

    rng = random.Random(seed)
    for p_idx, p in enumerate(paradigms):
        p_cases = by_paradigm[p]
        take = per_paradigm + (1 if p_idx < remainder else 0)
        selected.extend(p_cases[:take])

    return sorted(selected, key=lambda c: c.case_id)
