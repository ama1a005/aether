"""Model-free checks for prospective Qwen development capture."""

from __future__ import annotations

import torch

from instrumentation.run_qwen_development_capture import (
    _load_inputs,
    _paired_measurements,
)


def test_capture_partitions_are_disjoint_balanced_and_development_only() -> None:
    config, rows = _load_inputs()
    assert len(rows) == 20
    assert len(config["discovery_case_ids"]) == 16
    assert len(config["development_audit_case_ids"]) == 4
    partitions = [
        set(config["excluded_acceptance_case_ids"]),
        set(config["discovery_case_ids"]),
        set(config["development_audit_case_ids"]),
    ]
    assert set.intersection(*partitions) == set()
    assert len(set.union(*partitions)) == 24
    assert all(row["split"] == "development" and row["eligible"] for row in rows)
    for key in ("discovery_case_ids", "development_audit_case_ids"):
        selected = [row for row in rows if row["case_id"] in config[key]]
        assert sum(row["direction"] == "A_TO_B" for row in selected) == len(selected) // 2


def test_paired_measurements_are_complete_finite_and_not_ranked() -> None:
    clean = {
        "module.L0.mlp_output": torch.tensor([[1.0, 0.0]]),
        "head.L0.pre_o_proj_heads": torch.tensor([[[1.0], [2.0]]]),
    }
    attacked = {
        "module.L0.mlp_output": torch.tensor([[0.0, 1.0]]),
        "head.L0.pre_o_proj_heads": torch.tensor([[[2.0], [1.0]]]),
    }
    rows = _paired_measurements(clean, attacked)
    assert [row["component_id"] for row in rows] == sorted(clean)
    assert all(row["l2_distance"] > 0 for row in rows)
    assert all(-1.0 <= row["cosine_similarity"] <= 1.0 for row in rows)
    assert all("rank" not in row for row in rows)
