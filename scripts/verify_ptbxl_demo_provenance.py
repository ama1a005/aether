"""Verify the active demo cohort against official PTB-XL v1.0.3 metadata."""

from __future__ import annotations

import argparse
import ast
import csv
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOURCE_MANIFEST = ROOT / "demo/cases/ptbxl_source_manifest.json"
CASE_REGISTRY = ROOT / "demo/cases/ptbxl_demo_cases.json"


def _file_sha256(path: Path) -> str:
    """Return the lowercase SHA-256 digest for one file."""
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(data_root: Path) -> dict[str, Any]:
    """Fail closed unless every derived demo field agrees with pinned metadata."""
    manifest = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    registry = json.loads(CASE_REGISTRY.read_text(encoding="utf-8"))
    for name, expected in manifest["downloaded_files"].items():
        source = data_root / name
        if not source.is_file():
            raise FileNotFoundError(f"required PTB-XL source file is absent: {source}")
        if source.stat().st_size != expected["size_bytes"] or _file_sha256(source) != expected["sha256"]:
            raise ValueError(f"PTB-XL source identity mismatch: {name}")

    statements: dict[str, dict[str, str]] = {}
    with (data_root / "scp_statements.csv").open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            statements[row[""]] = row
    rows: dict[int, dict[str, str]] = {}
    selected = set(manifest["selection"]["selected_ecg_ids"])
    with (data_root / "ptbxl_database.csv").open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            ecg_id = int(row["ecg_id"])
            if ecg_id in selected:
                rows[ecg_id] = row
    if set(rows) != selected:
        raise ValueError("one or more selected PTB-XL records are absent")

    observed_ids: list[int] = []
    for case in registry["cases"]:
        provenance = case["provenance"]
        ecg_id = int(provenance["source_record_id"])
        row = rows[ecg_id]
        codes = ast.literal_eval(row["scp_codes"])
        classes = sorted({
            statements[code]["diagnostic_class"]
            for code in codes
            if code in statements
            and statements[code]["diagnostic"] in {"1", "1.0"}
            and statements[code]["diagnostic_class"]
        })
        expected_action = "DO_NOT_ESCALATE" if classes == ["NORM"] else "ESCALATE"
        checks = {
            "age": case["age"] == int(float(row["age"])),
            "sex": case["sex"] == manifest["derivation"]["sex_mapping"][row["sex"]],
            "fold": provenance["source_fold"] == int(row["strat_fold"]),
            "filename": provenance["source_file"] == row["filename_lr"],
            "codes": case["ecg"]["scp_codes"] == codes,
            "classes": case["ecg"]["diagnostic_superclasses"] == classes,
            "action": case["expected_action"] == expected_action,
        }
        if not all(checks.values()):
            raise ValueError(f"derived PTB-XL case mismatch for ECG {ecg_id}: {checks}")
        if int(row["strat_fold"]) not in range(1, 9):
            raise PermissionError(f"protected PTB-XL fold accessed by demo: {row['strat_fold']}")
        observed_ids.append(ecg_id)
    if observed_ids != manifest["selection"]["selected_ecg_ids"]:
        raise ValueError("demo case order differs from frozen PTB-XL selection")
    return {
        "overall": "PASS",
        "source_dataset": "PTB-XL v1.0.3",
        "case_count": len(observed_ids),
        "selected_ecg_ids": observed_ids,
        "protected_fold_access": 0,
        "waveforms_loaded": False,
        "claim_boundary": manifest["derivation"]["claim_boundary"],
    }


def main() -> None:
    """Verify a local official PTB-XL metadata download and print JSON."""
    parser = argparse.ArgumentParser()
    parser.add_argument("data_root", type=Path)
    print(json.dumps(verify(parser.parse_args().data_root), indent=2))


if __name__ == "__main__":
    main()
