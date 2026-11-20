"""Independent structural and provenance verification for Qwen SAE bundles."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

from causal.interventions.sae import load_sae_checkpoint
from experiments.phase1.qwen_sae_training import authorization, select_seed, sha256_file


def verify(root: Path) -> dict[str, Any]:
    """Reject incomplete, altered, split-unsafe, or noncanonical SAE evidence."""
    base, amendment = authorization()
    inventory_path = root / "archive_contents.json"
    if not inventory_path.is_file():
        raise FileNotFoundError("SAE bundle lacks archive_contents.json")
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    if not isinstance(inventory, dict) or not inventory:
        raise ValueError("SAE bundle inventory is empty")
    observed = {
        path.relative_to(root).as_posix(): sha256_file(path)
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.name != "archive_contents.json"
    }
    if observed != inventory:
        raise ValueError("SAE bundle inventory differs from retained artifacts")

    source = json.loads((root / "corpus/corpus_source_manifest.json").read_text(encoding="utf-8"))
    expected_corpus = amendment["training_corpus"]
    if source.get("dataset", {}).get("dataset_revision") != expected_corpus["dataset_revision"]:
        raise ValueError("SAE corpus revision mismatch")
    if source.get("selected_token_count") != expected_corpus["selected_token_count"]:
        raise ValueError("SAE corpus token count mismatch")
    tokens = np.load(root / "corpus/corpus_token_ids.npy", allow_pickle=False, mmap_mode="r")
    if tokens.shape != (65536,) or tokens.dtype != np.int64:
        raise ValueError("SAE token artifact is invalid")
    blocks = sorted((root / "activations").glob("block_*.npy"))
    if len(blocks) != 256:
        raise ValueError("SAE bundle does not contain exactly 256 corpus blocks")
    if any(np.load(path, allow_pickle=False, mmap_mode="r").shape != (256, 1536)
           for path in blocks):
        raise ValueError("SAE corpus activation block shape mismatch")

    summary = json.loads((root / "final/summary.json").read_text(encoding="utf-8"))
    if summary.get("scientific_outcome") == "SAE_REJECTED_NO_ELIGIBLE_SEED":
        if summary.get("overall") != "FAIL" or summary.get("selected_seed") is not None:
            raise ValueError("SAE negative summary is inconsistent")
        seed_summaries = [json.loads((root / f"seeds/seed-{seed}/seed_summary.json").read_text(encoding="utf-8"))
                          for seed in (11, 22, 33)]
        if any(item.get("scientific_outcome") != "SAE_SEED_REJECTED_NO_ELIGIBLE_CHECKPOINT"
               or item.get("epochs_completed") != 100 for item in seed_summaries):
            raise ValueError("SAE negative result lacks three completed rejected seeds")
        if (root / "audit").exists():
            raise ValueError("SAE negative result must not access the AETHER audit")
        if summary.get("validation_executions") != 0 or summary.get("test_executions") != 0:
            raise PermissionError("SAE negative result accessed a protected split")
        return {"bundle_valid": True, "scientific_outcome": summary["scientific_outcome"],
                "selected_seed": None, "corpus_blocks": len(blocks), "audit_records": 0,
                "validation_executions": 0, "test_executions": 0}

    selected = select_seed(root / "seeds")
    codec = load_sae_checkpoint(
        selected, expected_model_id=base["model_id"],
        expected_model_revision=base["model_revision"],
        expected_component_id=base["component_id"],
    )
    audit = json.loads(
        (root / "audit/aether_audit_activation_manifest.json").read_text(encoding="utf-8")
    )
    records = audit.get("records", [])
    if len(records) != 8 or {row.get("case_id") for row in records} != set(base["audit_case_ids"]):
        raise ValueError("SAE AETHER audit cohort mismatch")
    if audit.get("validation_executions") != 0 or audit.get("test_executions") != 0:
        raise PermissionError("SAE bundle accessed a protected split")
    if summary.get("selected_seed") != codec.provenance.training_seed:
        raise ValueError("SAE selected seed differs from final summary")
    if summary.get("validation_executions") != 0 or summary.get("test_executions") != 0:
        raise PermissionError("SAE final summary accessed a protected split")
    if summary.get("overall") not in {"PASS", "FAIL"}:
        raise ValueError("SAE final outcome is not retained")
    return {
        "bundle_valid": True,
        "scientific_outcome": summary["scientific_outcome"],
        "selected_seed": summary["selected_seed"],
        "corpus_blocks": len(blocks),
        "audit_records": len(records),
        "validation_executions": 0,
        "test_executions": 0,
    }


def main() -> None:
    """Verify a retained Qwen SAE bundle."""
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    print(json.dumps(verify(parser.parse_args().root), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
