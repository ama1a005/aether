"""Independent verifier for raw BFCL outputs and score artifacts."""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Sequence

from benchmarks.nov19_bfcl.preflight import PHASE1_CATEGORIES


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

        # Look for category score files or aggregate score file
        # Official BFCL evaluate writes score files under score_dir / model_name
        score_file = None
        candidate_score_files = [
            self.result_dir / "score.json",
            self.result_dir / "eval_score.json",
            self.result_dir / "eval_result.json",
        ]
        # Also check under adapter subdir
        sanitized_adapter = self.expected_model_adapter.replace("/", "_")
        candidate_score_files.extend([
            self.result_dir / sanitized_adapter / "score.json",
            self.result_dir / self.expected_model_adapter / "score.json",
        ])

        for cand in candidate_score_files:
            if cand.is_file():
                score_file = cand
                break

        # Check for per-category score files if aggregate is not found
        category_scores: dict[str, dict[str, Any]] = {}
        total_eligible = 0
        total_success = 0
        total_errors = 0

        for cat in self.expected_categories:
            cat_files = list(self.result_dir.rglob(f"*{cat}*.json"))
            if not cat_files:
                reasons.append(f"Missing evaluator output for category: {cat}")
                continue

            # Parse category files to ensure well-formedness and check task counts
            cat_task_ids = set()
            cat_eligible = 0
            cat_success = 0
            cat_errors = 0

            for cf in cat_files:
                try:
                    data = json.loads(cf.read_text(encoding="utf-8"))
                except Exception as exc:
                    reasons.append(f"Corrupt JSON in {cf.name}: {exc}")
                    continue

                # Process rows if structured as list or dict of records
                records = data if isinstance(data, list) else data.get("results", [])
                if isinstance(data, dict) and not records and "accuracy" in data:
                    # Aggregate category summary file
                    cat_eligible = data.get("total_cases", data.get("total", 0))
                    cat_success = data.get("correct", data.get("success", 0))
                    cat_errors = data.get("errors", 0)
                elif isinstance(records, list):
                    for rec in records:
                        tid = rec.get("id") or rec.get("task_id")
                        if tid:
                            if tid in cat_task_ids:
                                reasons.append(f"Duplicate task ID {tid} in {cf.name}")
                            cat_task_ids.add(tid)
                        cat_eligible += 1
                        if rec.get("valid") is False or rec.get("error"):
                            cat_errors += 1
                        elif rec.get("success") is True or rec.get("correct") is True:
                            cat_success += 1

            if cat_eligible == 0:
                reasons.append(f"Category {cat} has 0 eligible cases")
            else:
                category_scores[cat] = {
                    "eligible": cat_eligible,
                    "success": cat_success,
                    "errors": cat_errors,
                    "accuracy": cat_success / cat_eligible if cat_eligible > 0 else 0.0,
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
