"""Tests for the official-source PTB-XL demonstration boundary."""

from __future__ import annotations

import json
from pathlib import Path

from demo.backend.repository import load_cases


def test_active_demo_is_balanced_source_attributed_ptbxl_development_data() -> None:
    cases = load_cases()
    assert len(cases) == 12
    assert all(case.dataset_origin == "ptbxl_v1.0.3_physionet" for case in cases)
    assert all(case.provenance["source_fold"] in range(1, 9) for case in cases)
    assert all(case.provenance["license"] == "CC BY 4.0" for case in cases)
    assert {case.expected_action for case in cases} == {"ESCALATE", "DO_NOT_ESCALATE"}
    assert sum(case.expected_action == "ESCALATE" for case in cases) == 6
    assert all(not case.vitals and not case.labs for case in cases)


def test_source_manifest_discloses_derivation_and_no_official_execution_claim() -> None:
    manifest = json.loads(Path("demo/cases/ptbxl_source_manifest.json").read_text(encoding="utf-8"))
    assert manifest["source_dataset"] == "PTB-XL"
    assert manifest["waveforms_downloaded"] is False
    assert manifest["official_benchmark_execution"] is False
    assert manifest["derivation"]["claim_boundary"].startswith("The binary action is an AETHER")
