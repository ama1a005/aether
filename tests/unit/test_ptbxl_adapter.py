"""PTB-XL adapter tests use tiny constructed metadata, never benchmark results."""
import csv

import pytest

from benchmarks.ptbxl import load_ptbxl_cases
from target.case_loader import CaseLoader


def metadata(root):
    with (root / "scp_statements.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["", "diagnostic", "diagnostic_class"])
        writer.writeheader()
        writer.writerows([{"": "NORM", "diagnostic": 1, "diagnostic_class": "NORM"},
                          {"": "IMI", "diagnostic": 1, "diagnostic_class": "MI"},
                          {"": "RHY", "diagnostic": 0, "diagnostic_class": ""}])
    with (root / "ptbxl_database.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["ecg_id", "strat_fold", "scp_codes", "report"])
        writer.writeheader()
        writer.writerows([
            {"ecg_id": 1, "strat_fold": 1, "scp_codes": "{'NORM': 100.0}", "report": "private"},
            {"ecg_id": 2, "strat_fold": 1, "scp_codes": "{'NORM': 100, 'IMI': 80}", "report": "private"},
            {"ecg_id": 3, "strat_fold": 10, "scp_codes": "{'IMI': 100}", "report": "locked"}])


def test_metadata_adapter_labels_and_lock(tmp_path):
    metadata(tmp_path)
    cases = load_ptbxl_cases(tmp_path, folds=[1], n=2, seed=3)
    assert {case.ground_truth_decision for case in cases} == {"ESCALATE", "DO_NOT_ESCALATE"}
    assert all("report" not in case.features and case.ptbxl_fold == 1 for case in cases)
    assert CaseLoader("ptbxl", ptbxl_root=str(tmp_path)).load_cases(2, 3) == cases
    with pytest.raises(PermissionError, match="locked"):
        load_ptbxl_cases(tmp_path, folds=[10], n=1, seed=0)
    unlocked = load_ptbxl_cases(tmp_path, folds=[10], n=1, seed=0, allow_locked_test=True)
    assert unlocked[0].source_split == "fold_10"
    with pytest.raises(ValueError, match="only 2"):
        load_ptbxl_cases(tmp_path, folds=[1], n=3, seed=0)
