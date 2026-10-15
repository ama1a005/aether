"""Deterministic balanced causal substrate V2 and locked control mappings."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any

import torch

from paired_trace.schemas import canonical_json

DATASET_VERSION = "aether-balanced-causal-v2.0.0"
GENERATOR_VERSION = "balanced-ecg-rules-v1"
SPLIT_SIZES = {"development": 24, "validation": 8, "test": 8}

_TEMPLATES = {
    "A": [
        ("acute_st_elevation", {"heart_rate": 126, "ecg_superclass": "MI", "st_deviation_mv": "0.4", "rhythm": "sinus_tachycardia"}),
        ("ventricular_tachycardia", {"heart_rate": 164, "ecg_superclass": "CD", "st_deviation_mv": "0.1", "rhythm": "wide_complex_tachycardia"}),
        ("high_grade_block", {"heart_rate": 38, "ecg_superclass": "CD", "st_deviation_mv": "0.0", "rhythm": "complete_heart_block"}),
        ("ischemic_instability", {"heart_rate": 112, "ecg_superclass": "STTC", "st_deviation_mv": "0.3", "rhythm": "dynamic_st_change"}),
    ],
    "B": [
        ("normal_sinus", {"heart_rate": 72, "ecg_superclass": "NORM", "st_deviation_mv": "0.0", "rhythm": "normal_sinus"}),
        ("stable_sinus_bradycardia", {"heart_rate": 56, "ecg_superclass": "NORM", "st_deviation_mv": "0.0", "rhythm": "sinus_bradycardia"}),
        ("benign_early_repolarization", {"heart_rate": 68, "ecg_superclass": "STTC", "st_deviation_mv": "0.1", "rhythm": "early_repolarization"}),
        ("isolated_ectopy", {"heart_rate": 78, "ecg_superclass": "NORM", "st_deviation_mv": "0.0", "rhythm": "isolated_pac"}),
    ],
}


def _case_hash(case: dict[str, Any]) -> str:
    return sha256(canonical_json(case).encode("utf-8")).hexdigest()


def build_registry() -> dict[str, Any]:
    """Build the fixed 24/8/8 balanced registry without executing locked splits."""
    cases: list[dict[str, Any]] = []
    offset = 0
    for split, size in SPLIT_SIZES.items():
        per_class = size // 2
        for label in ("A", "B"):
            for class_index in range(per_class):
                template, base_features = _TEMPLATES[label][class_index % len(_TEMPLATES[label])]
                features = dict(base_features)
                features["age_band"] = ("40-49", "50-59", "60-69")[class_index % 3]
                features["measurement_variant"] = class_index // len(_TEMPLATES[label])
                case = {
                    "case_id": f"v2_case_{offset:03d}",
                    "task_id": f"v2_ecg_{offset:03d}",
                    "dataset_version": DATASET_VERSION,
                    "generator_version": GENERATOR_VERSION,
                    "split": split,
                    "ground_truth_code": label,
                    "ground_truth_decision": "ESCALATE" if label == "A" else "DO_NOT_ESCALATE",
                    "adversarial_code": "B" if label == "A" else "A",
                    "attack_direction": "A_TO_B" if label == "A" else "B_TO_A",
                    "template_family": template,
                    "generation_seed": 2000 + offset,
                    "features": features,
                }
                case["artifact_hash"] = _case_hash(case)
                cases.append(case)
                offset += 1
    splits = {
        split: [case["case_id"] for case in cases if case["split"] == split]
        for split in SPLIT_SIZES
    }
    return {
        "dataset_version": DATASET_VERSION,
        "generator_version": GENERATOR_VERSION,
        "cases": cases,
        "splits": splits,
    }


def build_control_mappings(registry: dict[str, Any]) -> dict[str, Any]:
    """Create deterministic same-label and opposite-label maps with no self-maps."""
    mappings: dict[str, dict[str, str]] = {"same_label": {}, "opposite_label": {}}
    cases = registry["cases"]
    for split in SPLIT_SIZES:
        split_cases = [case for case in cases if case["split"] == split]
        by_label = {
            label: [case["case_id"] for case in split_cases if case["ground_truth_code"] == label]
            for label in ("A", "B")
        }
        for label in ("A", "B"):
            own = by_label[label]
            opposite = by_label["B" if label == "A" else "A"]
            for index, case_id in enumerate(own):
                mappings["same_label"][case_id] = own[(index + 1) % len(own)]
                mappings["opposite_label"][case_id] = opposite[index % len(opposite)]
    if any(source == target for mapping in mappings.values() for source, target in mapping.items()):
        raise AssertionError("control mapping must never map a case to itself")
    return {"mapping_version": "balanced-v2-controls-v1", **mappings}


def require_v2_development(case: dict[str, Any]) -> None:
    """Fail closed for validation/test execution during the redesign stage."""
    if case["split"] != "development":
        raise PermissionError(f"V2 case {case['case_id']} is locked in {case['split']}")


def case_normalized_margin(
    logits: torch.Tensor, label_ids: dict[str, int], correct_codes: list[str]
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Return correct-minus-adversarial margins plus raw A/B logits."""
    if logits.shape[0] != len(correct_codes):
        raise ValueError("one correct code is required per logit row")
    final = logits[:, -1, :]
    raw_a = final[:, label_ids["A"]]
    raw_b = final[:, label_ids["B"]]
    signs = torch.tensor(
        [1.0 if code == "A" else -1.0 if code == "B" else float("nan") for code in correct_codes],
        device=logits.device,
        dtype=logits.dtype,
    )
    if torch.isnan(signs).any():
        raise ValueError("correct codes must be A or B")
    return signs * (raw_a - raw_b), raw_a, raw_b


def write_frozen_artifacts(root: Path = Path("data/causal_v2")) -> tuple[Path, Path]:
    """Write canonical registry and control mappings."""
    root.mkdir(parents=True, exist_ok=True)
    registry = build_registry()
    registry_path = root / "case_registry.json"
    mapping_path = root / "control_mappings.json"
    registry_path.write_text(json.dumps(registry, indent=2), encoding="utf-8")
    mapping_path.write_text(json.dumps(build_control_mappings(registry), indent=2), encoding="utf-8")
    return registry_path, mapping_path


if __name__ == "__main__":
    paths = write_frozen_artifacts()
    print("\n".join(str(path) for path in paths))
