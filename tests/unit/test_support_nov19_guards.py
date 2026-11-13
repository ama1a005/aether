"""Additional SUPPORT tests — split guard, evidence packet schema, checkpoint hash.

Section 9 compliance: explicit test coverage for split access blocking,
evidence packet v1 schema validation, and run resume checkpoint integrity.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from contracts.schemas import PatientCase
from experiments.supporting_nov19.red_team.adapter import (
    QUALIFIED_MODEL_ID,
    QUALIFIED_MODEL_REVISION,
    build_development_cases,
    validate_config,
)
from experiments.supporting_nov19.agent_c.runner import validate_agent_c_config
from experiments.supporting_nov19.sae.runner import validate_sae_config
from experiments.supporting_nov19.second_model.runner import validate_second_model_config


# ---------------------------------------------------------------------------
# Split guard tests — blocks QCI audit, validation, test splits
# ---------------------------------------------------------------------------

class TestSplitGuard(unittest.TestCase):
    """Verify that validation and test splits are rejected by all config validators."""

    def _make_red_team_config(self, split: str) -> dict:
        return {
            "schema_version": "supporting_nov19_v1",
            "model_id": QUALIFIED_MODEL_ID,
            "model_revision": QUALIFIED_MODEL_REVISION,
            "tokenizer_revision": QUALIFIED_MODEL_REVISION,
            "dtype": "float32",
            "device": "cpu",
            "split": split,
            "attack_families": ["tool_description_poison"],
            "max_target_calls": 8,
            "seed": 42,
            "drop_invalid": False,
            "output_dir": tempfile.mkdtemp(),
            "source_commit": "00846b020b685dfa3ab89bce2c5227d2810c9d1e",
        }

    def test_validation_split_blocked(self):
        """Red-team config with split='validation' must be rejected."""
        config = self._make_red_team_config("validation")
        errors = validate_config(config)
        self.assertTrue(any("split" in e.lower() for e in errors),
                        f"Expected split error, got: {errors}")

    def test_test_split_blocked(self):
        """Red-team config with split='test' must be rejected."""
        config = self._make_red_team_config("test")
        errors = validate_config(config)
        self.assertTrue(any("split" in e.lower() for e in errors),
                        f"Expected split error, got: {errors}")

    def test_development_split_allowed(self):
        """Red-team config with split='development' must pass split check."""
        config = self._make_red_team_config("development")
        errors = validate_config(config)
        self.assertFalse(any("split" in e.lower() for e in errors),
                         f"Unexpected split error: {errors}")

    def test_synthetic_split_allowed(self):
        """Red-team config with split='synthetic' must pass split check."""
        config = self._make_red_team_config("synthetic")
        errors = validate_config(config)
        self.assertFalse(any("split" in e.lower() for e in errors),
                         f"Unexpected split error: {errors}")

    def test_development_cases_never_use_blocked_splits(self):
        """All development cases must use allowed splits only."""
        blocked = {"validation", "test", "qci_audit"}
        for case in build_development_cases():
            self.assertNotIn(case.source_split, blocked,
                             f"Case {case.case_id} uses blocked split {case.source_split}")

    def test_development_cases_are_not_fixture_only(self):
        """Development cases used for real experiments must have fixture_only=False."""
        for case in build_development_cases():
            self.assertFalse(case.fixture_only,
                             f"Case {case.case_id} is fixture_only but used in real experiments")


# ---------------------------------------------------------------------------
# Evidence packet schema validation tests
# ---------------------------------------------------------------------------

EVIDENCE_PACKET_REQUIRED_FIELDS = [
    "schema_version",
    "experiment",
    "source_branch",
    "source_commit",
    "model_id",
    "model_revision",
    "split",
    "sample_count",
    "valid_count",
    "invalid_count",
    "error_count",
    "validation_accesses",
    "test_accesses",
    "raw_artifacts",
    "artifact_hashes",
    "status",
    "evidence_class",
    "claim_boundary",
]


class TestEvidencePacketSchema(unittest.TestCase):
    """Verify evidence packet schema compliance (Section 8.3)."""

    def _make_evidence_packet(self, experiment: str) -> dict:
        """Create a minimal valid evidence packet."""
        return {
            "schema_version": "aether.nov19.supporting-evidence.v1",
            "experiment": experiment,
            "source_branch": "amala",
            "source_commit": "00846b020b685dfa3ab89bce2c5227d2810c9d1e",
            "protocol_sha256": "",
            "model_id": QUALIFIED_MODEL_ID,
            "model_revision": QUALIFIED_MODEL_REVISION,
            "input_manifest_sha256": "",
            "split": "development",
            "sample_count": 4,
            "valid_count": 4,
            "invalid_count": 0,
            "error_count": 0,
            "validation_accesses": 0,
            "test_accesses": 0,
            "raw_artifacts": [],
            "artifact_hashes": {},
            "status": "EXECUTED",
            "evidence_class": "real_model_cpu_float32",
            "claim_boundary": "Development cohort only.",
        }

    def test_evidence_packet_has_all_required_fields(self):
        """A valid evidence packet must contain all Section 8.3 fields."""
        packet = self._make_evidence_packet("SUPPORT-01-test")
        for field in EVIDENCE_PACKET_REQUIRED_FIELDS:
            self.assertIn(field, packet, f"Missing required field: {field}")

    def test_schema_version_is_correct(self):
        """Schema version must be 'aether.nov19.supporting-evidence.v1'."""
        packet = self._make_evidence_packet("SUPPORT-01-test")
        self.assertEqual(packet["schema_version"],
                         "aether.nov19.supporting-evidence.v1")

    def test_validation_accesses_is_zero(self):
        """Supporting experiments must not access validation split."""
        packet = self._make_evidence_packet("SUPPORT-01-test")
        self.assertEqual(packet["validation_accesses"], 0)

    def test_test_accesses_is_zero(self):
        """Supporting experiments must not access test split."""
        packet = self._make_evidence_packet("SUPPORT-01-test")
        self.assertEqual(packet["test_accesses"], 0)

    def test_evidence_class_is_real_model(self):
        """Evidence class for real execution must indicate real model."""
        packet = self._make_evidence_packet("SUPPORT-01-test")
        self.assertTrue(packet["evidence_class"].startswith("real_model"),
                        f"Evidence class must be real_model_*, got {packet['evidence_class']}")

    def test_status_is_valid_enum(self):
        """Status must be one of the defined status values."""
        valid_statuses = {"EXECUTED", "DRY_RUN", "BLOCKED", "PARTIAL", "ERROR"}
        packet = self._make_evidence_packet("SUPPORT-01-test")
        self.assertIn(packet["status"], valid_statuses)

    def test_claim_boundary_is_nonempty(self):
        """Claim boundary must be a non-empty string explaining scope."""
        packet = self._make_evidence_packet("SUPPORT-01-test")
        self.assertIsInstance(packet["claim_boundary"], str)
        self.assertTrue(len(packet["claim_boundary"]) > 0)

    def test_packet_is_json_serializable(self):
        """Evidence packet must be fully JSON-serializable."""
        packet = self._make_evidence_packet("SUPPORT-01-test")
        serialized = json.dumps(packet)
        deserialized = json.loads(serialized)
        self.assertEqual(packet, deserialized)


# ---------------------------------------------------------------------------
# Run resume / checkpoint hash tests
# ---------------------------------------------------------------------------

class TestRunResumeCheckpointHash(unittest.TestCase):
    """Tests for run checkpoint integrity during resume scenarios."""

    def test_config_source_commit_must_be_present(self):
        """Red-team config without source_commit is rejected."""
        config = {
            "schema_version": "supporting_nov19_v1",
            "model_id": QUALIFIED_MODEL_ID,
            "model_revision": QUALIFIED_MODEL_REVISION,
            "tokenizer_revision": QUALIFIED_MODEL_REVISION,
            "dtype": "float32",
            "device": "cpu",
            "split": "development",
            "attack_families": ["tool_description_poison"],
            "max_target_calls": 8,
            "seed": 42,
            "drop_invalid": False,
            "output_dir": tempfile.mkdtemp(),
            # source_commit intentionally missing
        }
        errors = validate_config(config)
        self.assertTrue(any("source_commit" in e for e in errors))

    def test_agent_c_config_requires_source_commit(self):
        """Agent C config without source_commit is rejected."""
        config = {
            "model_id": QUALIFIED_MODEL_ID,
            "model_revision": QUALIFIED_MODEL_REVISION,
            "agent_c_config": {},
            "output_dir": "results/test",
            # source_commit missing
        }
        errors = validate_agent_c_config(config)
        self.assertTrue(any("source_commit" in e for e in errors))

    def test_sae_config_requires_source_commit(self):
        """SAE config without source_commit is rejected."""
        config = {
            "model_id": QUALIFIED_MODEL_ID,
            "model_revision": QUALIFIED_MODEL_REVISION,
            "component_id": "sender.module.L22.attention_output",
            "output_dir": "results/test",
            # source_commit missing
        }
        errors = validate_sae_config(config)
        self.assertTrue(any("source_commit" in e for e in errors))

    def test_second_model_config_requires_source_commit(self):
        """Second model config without source_commit is rejected."""
        config = {
            "model_id": "microsoft/Phi-3-mini-4k-instruct",
            "model_revision": "abc123def456",
            "dtype": "float32",
            "device": "cpu",
            "output_dir": "results/test",
            # source_commit missing
        }
        errors = validate_second_model_config(config)
        self.assertTrue(any("source_commit" in e for e in errors))

    def test_non_empty_output_dir_prevents_overwrite(self):
        """A non-empty output dir is rejected to prevent evidence overwrite."""
        with tempfile.TemporaryDirectory() as td:
            # Create a file in the output dir
            (Path(td) / "existing_evidence.json").write_text("{}")
            config = {
                "schema_version": "supporting_nov19_v1",
                "model_id": QUALIFIED_MODEL_ID,
                "model_revision": QUALIFIED_MODEL_REVISION,
                "tokenizer_revision": QUALIFIED_MODEL_REVISION,
                "dtype": "float32",
                "device": "cpu",
                "split": "development",
                "attack_families": ["tool_description_poison"],
                "max_target_calls": 8,
                "seed": 42,
                "drop_invalid": False,
                "output_dir": td,
                "source_commit": "00846b020b685dfa3ab89bce2c5227d2810c9d1e",
            }
            errors = validate_config(config)
            self.assertTrue(any("non-empty" in e.lower() or "overwrite" in e.lower()
                                for e in errors),
                            f"Expected overwrite prevention error, got: {errors}")


# ---------------------------------------------------------------------------
# SAE trainer unit tests
# ---------------------------------------------------------------------------

class TestSAETrainerUnit(unittest.TestCase):
    """Unit tests for the SAE trainer module."""

    def test_trainer_initializes(self):
        """SAE trainer must initialize with valid parameters."""
        from experiments.supporting_nov19.sae.trainer import SAETrainer
        trainer = SAETrainer(input_dim=64, latent_dim=32, seed=42)
        self.assertEqual(trainer.input_dim, 64)
        self.assertEqual(trainer.latent_dim, 32)
        self.assertEqual(trainer.encoder_weight.shape, (64, 32))
        self.assertEqual(trainer.decoder_weight.shape, (32, 64))

    def test_trainer_forward_shape(self):
        """Forward pass must produce correct output shape."""
        import numpy as np
        from experiments.supporting_nov19.sae.trainer import SAETrainer
        trainer = SAETrainer(input_dim=64, latent_dim=32, seed=42)
        x = np.random.randn(8, 64).astype(np.float32)
        x_hat, z_pre, z = trainer.forward(x)
        self.assertEqual(x_hat.shape, (8, 64))
        self.assertEqual(z_pre.shape, (8, 32))
        self.assertEqual(z.shape, (8, 32))

    def test_trainer_train_reduces_loss(self):
        """Training must reduce reconstruction loss over epochs."""
        import numpy as np
        from experiments.supporting_nov19.sae.trainer import SAETrainer
        np.random.seed(42)
        data = np.random.randn(100, 32).astype(np.float32)
        trainer = SAETrainer(input_dim=32, latent_dim=16, lr=0.01, seed=42)
        history = trainer.train(data, epochs=20, batch_size=32, verbose=False)
        # Loss should decrease
        self.assertLess(history[-1]["recon_loss"], history[0]["recon_loss"])

    def test_trainer_save_checkpoint_creates_files(self):
        """Checkpoint save must create metadata.json and weights.npz."""
        import numpy as np
        from experiments.supporting_nov19.sae.trainer import SAETrainer
        trainer = SAETrainer(input_dim=32, latent_dim=16, seed=42)
        data = np.random.randn(50, 32).astype(np.float32)
        trainer.train(data, epochs=2, batch_size=16, verbose=False)
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "ckpt"
            trainer.save_checkpoint(out, component_id="test.component")
            self.assertTrue((out / "metadata.json").is_file())
            self.assertTrue((out / "weights.npz").is_file())
            # Verify metadata is valid JSON
            meta = json.loads((out / "metadata.json").read_text())
            self.assertEqual(meta["schema_version"], 1)
            self.assertEqual(meta["component_id"], "test.component")
            self.assertEqual(meta["input_dim"], 32)
            self.assertEqual(meta["latent_dim"], 16)

    def test_ablate_features_zeros_selected(self):
        """Zero ablation must set selected features to zero."""
        import numpy as np
        from experiments.supporting_nov19.sae.trainer import SAETrainer, ablate_features
        trainer = SAETrainer(input_dim=16, latent_dim=8, seed=42)
        x = np.random.randn(4, 16).astype(np.float32)
        weights = {
            "encoder_weight": trainer.encoder_weight,
            "encoder_bias": trainer.encoder_bias,
            "decoder_weight": trainer.decoder_weight,
            "decoder_bias": trainer.decoder_bias,
            "mean": trainer.mean,
            "scale": trainer.scale,
        }
        result = ablate_features(x, weights, [0, 1, 2], method="zero")
        self.assertEqual(result.shape, (4, 16))

    def test_patch_features_shape(self):
        """Activation patching must produce correct output shape."""
        import numpy as np
        from experiments.supporting_nov19.sae.trainer import SAETrainer, patch_features
        trainer = SAETrainer(input_dim=16, latent_dim=8, seed=42)
        src = np.random.randn(4, 16).astype(np.float32)
        tgt = np.random.randn(4, 16).astype(np.float32)
        weights = {
            "encoder_weight": trainer.encoder_weight,
            "encoder_bias": trainer.encoder_bias,
            "decoder_weight": trainer.decoder_weight,
            "decoder_bias": trainer.decoder_bias,
            "mean": trainer.mean,
            "scale": trainer.scale,
        }
        result = patch_features(src, tgt, weights, [3, 5])
        self.assertEqual(result.shape, (4, 16))

    def test_mean_baseline_computation(self):
        """Mean baseline must return a valid relative error."""
        import numpy as np
        from experiments.supporting_nov19.sae.trainer import compute_mean_baseline
        data = np.random.randn(50, 16).astype(np.float32)
        baseline = compute_mean_baseline(data)
        self.assertIsInstance(baseline, float)
        self.assertGreater(baseline, 0.0)
        self.assertLess(baseline, 2.0)  # Should be reasonable

    def test_zero_baseline_is_one(self):
        """Zero reconstruction baseline must return 1.0."""
        import numpy as np
        from experiments.supporting_nov19.sae.trainer import compute_zero_baseline
        data = np.random.randn(50, 16).astype(np.float32)
        baseline = compute_zero_baseline(data)
        self.assertEqual(baseline, 1.0)


# ---------------------------------------------------------------------------
# Data loader tests
# ---------------------------------------------------------------------------

class TestActivationDataLoader(unittest.TestCase):
    """Tests for the hash-verifying activation data loader."""

    def test_loader_finds_npy_file(self):
        """Loader must find .npy files in the data directory."""
        import numpy as np
        from experiments.supporting_nov19.sae.data_loader import ActivationLoader
        with tempfile.TemporaryDirectory() as td:
            data = np.random.randn(20, 8).astype(np.float32)
            np.save(os.path.join(td, "test_component.npy"), data)
            loader = ActivationLoader(
                data_dir=Path(td),
                component_id="test.component",
            )
            loaded = loader.load()
            self.assertEqual(loaded.shape, (20, 8))

    def test_loader_rejects_wrong_hash(self):
        """Loader must reject data with wrong SHA256."""
        import numpy as np
        from experiments.supporting_nov19.sae.data_loader import ActivationLoader
        with tempfile.TemporaryDirectory() as td:
            data = np.random.randn(10, 4).astype(np.float32)
            np.save(os.path.join(td, "test_component.npy"), data)
            loader = ActivationLoader(
                data_dir=Path(td),
                component_id="test.component",
                expected_sha256="0000000000000000000000000000000000000000000000000000000000000000",
            )
            with self.assertRaises(ValueError):
                loader.load()

    def test_loader_iter_batches(self):
        """Loader must yield correct batch sizes."""
        import numpy as np
        from experiments.supporting_nov19.sae.data_loader import ActivationLoader
        with tempfile.TemporaryDirectory() as td:
            data = np.random.randn(100, 8).astype(np.float32)
            np.save(os.path.join(td, "test_component.npy"), data)
            loader = ActivationLoader(data_dir=Path(td), component_id="test.component")
            batches = list(loader.iter_batches(batch_size=32))
            # 100 samples / 32 batch = 4 batches (32, 32, 32, 4)
            self.assertEqual(len(batches), 4)
            self.assertEqual(batches[0].shape[0], 32)
            self.assertEqual(batches[-1].shape[0], 4)

    def test_loader_split_train_eval(self):
        """Loader must split data into train and eval sets."""
        import numpy as np
        from experiments.supporting_nov19.sae.data_loader import ActivationLoader
        with tempfile.TemporaryDirectory() as td:
            data = np.random.randn(100, 8).astype(np.float32)
            np.save(os.path.join(td, "test_component.npy"), data)
            loader = ActivationLoader(data_dir=Path(td), component_id="test.component")
            train, eval_ = loader.split_train_eval(eval_fraction=0.2)
            self.assertEqual(train.shape[0] + eval_.shape[0], 100)
            self.assertEqual(eval_.shape[0], 20)

    def test_loader_manifest(self):
        """Loader manifest must contain required metadata fields."""
        import numpy as np
        from experiments.supporting_nov19.sae.data_loader import ActivationLoader
        with tempfile.TemporaryDirectory() as td:
            data = np.random.randn(50, 8).astype(np.float32)
            np.save(os.path.join(td, "test_component.npy"), data)
            loader = ActivationLoader(data_dir=Path(td), component_id="test.component")
            manifest = loader.get_manifest()
            self.assertEqual(manifest["n_samples"], 50)
            self.assertEqual(manifest["input_dim"], 8)
            self.assertEqual(manifest["component_id"], "test.component")


if __name__ == "__main__":
    unittest.main()
