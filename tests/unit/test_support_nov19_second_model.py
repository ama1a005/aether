"""Unit tests for SUPPORT-04: Second model qualification runner."""
from __future__ import annotations

import pytest

from experiments.supporting_nov19.second_model.runner import (
    DISQUALIFIED_MODELS,
    PRIMARY_MODEL_ID,
    SECOND_MODEL_ID,
    validate_second_model_config,
)
from experiments.supporting_nov19.red_team.adapter import QUALIFIED_MODEL_REVISION


def _valid_second_model_config() -> dict:
    return {
        "schema_version": "aether.supporting-nov19.second-model.v1",
        "model_id": SECOND_MODEL_ID,
        "model_revision": "abc123def456" * 3,  # fake pinned revision for testing
        "tokenizer_revision": "abc123def456" * 3,
        "dtype": "float32",
        "device": "cpu",
        "seed": 0,
        "output_dir": "/tmp/second_model_out",
        "source_commit": "00846b020b685dfa3ab89bce2c5227d2810c9d1e",
    }


class TestValidateSecondModelConfig:
    def test_valid_config_passes(self):
        errors = validate_second_model_config(_valid_second_model_config())
        assert errors == []

    def test_primary_model_as_second_rejected(self):
        config = _valid_second_model_config()
        config["model_id"] = PRIMARY_MODEL_ID
        errors = validate_second_model_config(config)
        assert any("primary model" in e or "not" in e for e in errors)

    def test_disqualified_model_rejected(self):
        for model_id in DISQUALIFIED_MODELS:
            config = _valid_second_model_config()
            config["model_id"] = model_id
            errors = validate_second_model_config(config)
            assert any("disqualified" in e.lower() or "failed" in e.lower() or
                       "balanced" in e.lower() for e in errors), \
                f"Expected rejection for disqualified model {model_id!r}"

    def test_unknown_model_revision_rejected(self):
        config = _valid_second_model_config()
        config["model_revision"] = "unknown"
        errors = validate_second_model_config(config)
        assert any("model_revision" in e for e in errors)

    def test_empty_model_revision_rejected(self):
        config = _valid_second_model_config()
        config["model_revision"] = ""
        errors = validate_second_model_config(config)
        assert any("model_revision" in e for e in errors)

    def test_missing_output_dir_rejected(self):
        config = _valid_second_model_config()
        del config["output_dir"]
        errors = validate_second_model_config(config)
        assert any("output_dir" in e for e in errors)

    def test_qwen_05b_disqualified(self):
        """Explicitly verify 0.5B cannot be declared as passing second model."""
        config = _valid_second_model_config()
        config["model_id"] = "Qwen/Qwen2.5-0.5B-Instruct"
        config["model_revision"] = "7ae557604adf67be50417f59c2c2f167def9a775"
        errors = validate_second_model_config(config)
        assert len(errors) > 0, (
            "Qwen 0.5B failed balanced qualification and must be rejected as second model"
        )


class TestDisqualifiedModelsList:
    def test_qwen_05b_in_disqualified(self):
        assert "Qwen/Qwen2.5-0.5B-Instruct" in DISQUALIFIED_MODELS

    def test_primary_model_not_in_disqualified(self):
        # Primary is separately guarded; must not silently pass through
        assert PRIMARY_MODEL_ID not in DISQUALIFIED_MODELS
