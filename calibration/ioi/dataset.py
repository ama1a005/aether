"""Deterministic IOI clean/corrupted prompt construction."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class IOIExample:
    """One length-matched clean/corrupted IOI calibration pair."""

    pair_id: str
    clean_prompt: str
    corrupted_prompt: str
    io_name: str
    subject_name: str


NAME_PAIRS = [
    ("Mary", "John"),
    ("Sarah", "Michael"),
    ("David", "James"),
    ("Robert", "Daniel"),
    ("Jessica", "Matthew"),
    ("Ashley", "Jennifer"),
    ("Joshua", "Amanda"),
    ("Andrew", "Ryan"),
    ("Jason", "Justin"),
    ("William", "Brian"),
    ("Nicole", "Anthony"),
    ("Eric", "Adam"),
]


def build_fixed_ioi_dataset() -> list[IOIExample]:
    """Build 24 fixed BABA/ABBA-style pairs without sampling or cherry-picking."""
    examples: list[IOIExample] = []
    for index, (io_name, subject_name) in enumerate(NAME_PAIRS):
        for orientation, first, second in (
            ("baba", subject_name, io_name),
            ("abba", io_name, subject_name),
        ):
            prefix = f"Then, {first} and {second} went to the store."
            clean = f"{prefix} {subject_name} gave a ring to"
            corrupted = f"{prefix} {io_name} gave a ring to"
            examples.append(
                IOIExample(
                    pair_id=f"ioi_{index:02d}_{orientation}",
                    clean_prompt=clean,
                    corrupted_prompt=corrupted,
                    io_name=io_name,
                    subject_name=subject_name,
                )
            )
    return examples


def validate_with_tokenizer(examples: list[IOIExample], tokenizer: Any) -> None:
    """Validate name-token and paired-length assumptions for GPT-2 tokenization."""
    for example in examples:
        io_ids = tokenizer.encode(" " + example.io_name, add_special_tokens=False)
        subject_ids = tokenizer.encode(" " + example.subject_name, add_special_tokens=False)
        if len(io_ids) != 1 or len(subject_ids) != 1:
            raise ValueError(f"names must be single GPT-2 tokens: {example.pair_id}")
        clean_ids = tokenizer.encode(example.clean_prompt, add_special_tokens=False)
        corrupt_ids = tokenizer.encode(example.corrupted_prompt, add_special_tokens=False)
        if len(clean_ids) != len(corrupt_ids):
            raise ValueError(f"paired token lengths differ: {example.pair_id}")


def write_dataset(examples: list[IOIExample], path: Path, tokenizer_revision: str) -> str:
    """Write immutable prompt content and return its SHA-256 hash."""
    payload = {
        "schema_version": "1.0.0",
        "seed": 0,
        "sampling": "none_fixed_enumeration",
        "tokenizer_revision": tokenizer_revision,
        "examples": [asdict(example) for example in examples],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return sha256(path.read_bytes()).hexdigest()
