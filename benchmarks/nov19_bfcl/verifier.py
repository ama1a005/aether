"""Independent verifier for raw BFCL outputs and score artifacts."""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Sequence

from benchmarks.nov19_bfcl.preflight import PHASE1_CATEGORIES
from benchmarks.bfcl_compat import official_categories


@dataclass(frozen=True)
class VerificationResult:
    """Result of independent artifact verification."""
    passed: bool
    reasons: tuple[str, ...]
    metrics: dict[str, Any] = field(default_factory=dict)
    artifact_hashes: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "reasons": list(self.reasons),
            "metrics": self.metrics,
            "artifact_hashes": self.artifact_hashes,
        }


class BFCLArtifactVerifier:
    """Verifies that BFCL generation and scoring artifacts are complete and untampered."""

    def __init__(
        self,
        result_dir: Path,
        expected_categories: Sequence[str] = PHASE1_CATEGORIES,
        expected_model_adapter: str = "AETHER/Qwen2.5-1.5B-Instruct-FC",
    ) -> None:
        self.result_dir = Path(result_dir)
        self.expected_categories = tuple(expected_categories)
        self.expected_model_adapter = expected_model_adapter

    def verify(self) -> VerificationResult:
        """Audit result directory without trusting summary claims."""
        reasons = []
        artifact_hashes: dict[str, str] = {}
        metrics: dict[str, Any] = {"categories": {}}

        if not self.result_dir.is_dir():
            return VerificationResult(
                passed=False,
                reasons=(f"Result directory does not exist: {self.result_dir}",),
            )

        # Hash all JSON and log files in the result directory
        all_files = sorted(self.result_dir.rglob("*.json"))
        if not all_files:
            return VerificationResult(
                passed=False,
                reasons=(f"No JSON result artifacts found in {self.result_dir}",),
            )

        for f in all_files:
            rel = str(f.relative_to(self.result_dir))
            digest = sha256(f.read_bytes()).hexdigest()
            artifact_hashes[rel] = digest

        category_scores: dict[str, dict[str, Any]] = {}
        total_eligible = 0
        total_success = 0
        total_errors = 0

        translated = official_categories(self.expected_categories)
        adapter_dir = self.result_dir / self.expected_model_adapter.replace("/", "_")
        for cat, cli_cat in zip(self.expected_categories, translated, strict=True):
            result_files = list(adapter_dir.rglob(f"BFCL_v4_{cli_cat}_result.json"))
            score_files = list(adapter_dir.rglob(f"BFCL_v4_{cli_cat}_score.json"))
            if len(result_files) != 1 or len(score_files) != 1:
                reasons.append(
                    f"Expected one official result and score file for {cat} ({cli_cat}); "
                    f"found {len(result_files)} result and {len(score_files)} score files"
                )
                continue
            try:
                result_rows = self._read_json_lines(result_files[0])
                score_rows = self._read_json_lines(score_files[0])
            except ValueError as exc:
                reasons.append(str(exc))
                continue
            if not score_rows or not isinstance(score_rows[0], dict):
                reasons.append(f"Official score header absent for category {cat}")
                continue
            header = score_rows[0]
            cat_eligible = header.get("total_count")
            cat_success = header.get("correct_count")
            accuracy = header.get("accuracy")
            if not isinstance(cat_eligible, int) or not isinstance(cat_success, int):
                reasons.append(f"Invalid official score counts for category {cat}")
                continue
            if cat_eligible <= 0:
                reasons.append(f"Category {cat} has 0 eligible cases")
                continue
            if not 0 <= cat_success <= cat_eligible or len(result_rows) != cat_eligible:
                reasons.append(f"Official result/count mismatch for category {cat}")
                continue
            expected_accuracy = cat_success / cat_eligible
            if not isinstance(accuracy, (int, float)) or abs(float(accuracy) - expected_accuracy) > 1e-12:
                reasons.append(f"Official accuracy/count mismatch for category {cat}")
                continue
            ids = [row.get("id") for row in result_rows]
            if any(not isinstance(item, str) or not item for item in ids) or len(set(ids)) != len(ids):
                reasons.append(f"Missing or duplicate official task IDs for category {cat}")
                continue
            cat_errors = sum(
                isinstance(row.get("result"), str)
                and row["result"].startswith("Error during inference:")
                for row in result_rows
            )
            category_scores[cat] = {
                "official_category": cli_cat,
                "eligible": cat_eligible,
                "success": cat_success,
                "errors": cat_errors,
                "accuracy": expected_accuracy,
            }
            total_eligible += cat_eligible
            total_success += cat_success
            total_errors += cat_errors

        metrics["categories"] = category_scores
        metrics["total_eligible"] = total_eligible
        metrics["total_success"] = total_success
        metrics["total_errors"] = total_errors
        metrics["overall_accuracy"] = (
            total_success / total_eligible if total_eligible > 0 else 0.0
        )

        passed = len(reasons) == 0 and len(category_scores) == len(self.expected_categories)
        return VerificationResult(
            passed=passed,
            reasons=tuple(reasons),
            metrics=metrics,
            artifact_hashes=artifact_hashes,
        )

    @staticmethod
    def _read_json_lines(path: Path) -> list[dict[str, Any]]:
        """Read BFCL's newline-delimited `.json` artifacts without coercion."""
        rows: list[dict[str, Any]] = []
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Corrupt JSONL in {path.name} line {line_number}: {exc}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"Non-object JSONL row in {path.name} line {line_number}")
            rows.append(row)
        return rows
