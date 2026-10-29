"""Deterministic PTB-XL metadata adapter; raw ECG waveforms are never exposed."""
from __future__ import annotations

import ast
import csv
from pathlib import Path
import random
from typing import Sequence

from contracts.schemas import PatientCase


def load_ptbxl_cases(data_root: Path, *, folds: Sequence[int], n: int,
                     seed: int, allow_locked_test: bool = False) -> list[PatientCase]:
    """Build structured cases from official metadata and diagnostic superclasses.

    Fold 10 is rejected unless a caller explicitly unlocks it. This adapter does
    not download data and does not read waveform files or free-text reports.
    Any diagnostic superclass other than NORM maps to ESCALATE.
    """
    normalized_folds = tuple(sorted(folds))
    if (not normalized_folds or len(set(normalized_folds)) != len(normalized_folds)
            or any(type(fold) is not int or fold < 1 or fold > 10 for fold in normalized_folds)):
        raise ValueError("PTB-XL folds must be unique integers from 1 to 10")
    if 10 in normalized_folds and not allow_locked_test:
        raise PermissionError("PTB-XL fold 10 is locked")
    if type(n) is not int or n < 1 or type(seed) is not int:
        raise ValueError("n must be positive and seed must be an integer")
    database = data_root / "ptbxl_database.csv"
    statements = data_root / "scp_statements.csv"
    if not database.is_file() or not statements.is_file():
        raise FileNotFoundError("PTB-XL v1.0.3 metadata files are required")
    code_to_class: dict[str, str] = {}
    with statements.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            code = row.get("") or row.get("code")
            diagnostic = row.get("diagnostic", "").strip()
            superclass = row.get("diagnostic_class", "").strip()
            if code and superclass and diagnostic in {"1", "1.0"}:
                code_to_class[code] = superclass
    if not code_to_class:
        raise ValueError("No diagnostic superclass mapping found")
    candidates: list[PatientCase] = []
    with database.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            try:
                fold = int(row["strat_fold"])
                ecg_id = int(row["ecg_id"])
                codes = ast.literal_eval(row["scp_codes"])
            except (KeyError, ValueError, SyntaxError) as exc:
                raise ValueError("Invalid PTB-XL metadata row") from exc
            if fold not in normalized_folds:
                continue
            if not isinstance(codes, dict) or any(not isinstance(code, str) for code in codes):
                raise ValueError(f"Invalid scp_codes for ECG {ecg_id}")
            classes = sorted({code_to_class[code] for code in codes if code in code_to_class})
            if not classes:
                continue
            abnormal = any(label != "NORM" for label in classes)
            candidates.append(PatientCase(
                case_id=f"ptbxl_{ecg_id:05d}",
                features={"diagnostic_superclasses": classes},
                ground_truth_decision="ESCALATE" if abnormal else "DO_NOT_ESCALATE",
                source_dataset="ptbxl_v1.0.3", source_split=f"fold_{fold}",
                ptbxl_fold=fold, metadata={"ecg_id": ecg_id,
                    "derivation": "official_scp_codes_to_diagnostic_class"}))
    candidates.sort(key=lambda case: case.case_id)
    if len(candidates) < n:
        raise ValueError(f"Requested {n} cases but only {len(candidates)} eligible cases exist")
    return random.Random(seed).sample(candidates, n)
