"""Tests for provenance-locked conversion of retained Qwen activations."""

import json

import numpy as np
import pytest
import torch

from experiments.supporting_nov19.sae.activation_dataset import build_activation_dataset


def _capture(path, value: float) -> None:
    torch.save({"module.L22.attention_output": torch.full((1, 4), value)}, path)


def test_builder_selects_exact_role_condition_and_records_sources(tmp_path) -> None:
    source = tmp_path / "captures"
    source.mkdir()
    _capture(source / "v2_case_002_receiver_clean.pt", 1.0)
    _capture(source / "v2_case_002_receiver_attacked.pt", 2.0)
    _capture(source / "v2_case_002_sender_clean.pt", 3.0)

    data, manifest_path = build_activation_dataset(
        source, tmp_path / "dataset",
        component_id="receiver.module.L22.attention_output", condition="clean",
    )
    matrix = np.load(data, allow_pickle=False)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert matrix.shape == (1, 4)
    assert np.all(matrix == 1.0)
    assert manifest["source_count"] == 1
    assert manifest["sources"][0]["condition"] == "clean"
    assert len(manifest["dataset_sha256"]) == 64


def test_builder_fails_closed_for_missing_component(tmp_path) -> None:
    source = tmp_path / "captures"
    source.mkdir()
    torch.save({"module.L0.mlp_output": torch.ones(1, 4)},
               source / "v2_case_002_receiver_clean.pt")
    with pytest.raises(ValueError, match="lacks exact component"):
        build_activation_dataset(
            source, tmp_path / "dataset",
            component_id="receiver.module.L22.attention_output", condition="clean",
        )


def test_builder_never_overwrites_existing_output(tmp_path) -> None:
    source = tmp_path / "captures"
    source.mkdir()
    output = tmp_path / "dataset"
    output.mkdir()
    with pytest.raises(FileExistsError):
        build_activation_dataset(
            source, output,
            component_id="receiver.module.L22.attention_output", condition="clean",
        )
