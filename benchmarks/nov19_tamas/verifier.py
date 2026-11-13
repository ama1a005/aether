"""Independent verifier for TAMAS multi-agent traces and evaluation outputs."""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from benchmarks.nov19_tamas.case import ATTACK_TYPES, OFFICIAL_COMMIT


@dataclass(frozen=True)
class TAMASVerificationResult:
    """Outcome of TAMAS artifact verification."""
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


class TAMASArtifactVerifier:
    """Audits TAMAS result artifacts for trace fidelity, judge provenance, and denominator safety."""

    def __init__(self, result_dir: Path) -> None:
        self.result_dir = Path(result_dir)

    def verify(self) -> TAMASVerificationResult:
        reasons = []
        artifact_hashes: dict[str, str] = {}
        metrics: dict[str, Any] = {}

        if not self.result_dir.is_dir():
            return TAMASVerificationResult(
                passed=False,
                reasons=(f"Result directory does not exist: {self.result_dir}",),
            )

        json_files = sorted(self.result_dir.glob("*.json"))
        if not json_files:
            return TAMASVerificationResult(
                passed=False,
                reasons=(f"No JSON artifacts found in {self.result_dir}",),
            )

        for jf in json_files:
            artifact_hashes[jf.name] = sha256(jf.read_bytes()).hexdigest()

        # Check for records file
        records_path = self.result_dir / "trajectories.json"
        if not records_path.is_file():
            records_path = self.result_dir / "adapter_rows.json"

        if not records_path.is_file():
            reasons.append(f"Missing trajectories/records file in {self.result_dir}")
            return TAMASVerificationResult(
                passed=False,
                reasons=tuple(reasons),
                artifact_hashes=artifact_hashes,
            )

        try:
            records = json.loads(records_path.read_text(encoding="utf-8"))
        except Exception as exc:
            return TAMASVerificationResult(
                passed=False,
                reasons=(f"Unreadable records JSON: {exc}",),
                artifact_hashes=artifact_hashes,
            )

        if not isinstance(records, list) or not records:
            return TAMASVerificationResult(
                passed=False,
                reasons=("Records must be a non-empty list",),
                artifact_hashes=artifact_hashes,
            )

        seen_ids = set()
        by_attack: dict[str, dict[str, int]] = {at: {"total": 0, "success": 0, "invalid": 0, "error": 0} for at in ATTACK_TYPES}
        eval_methods = set()
        judge_models = set()
        origins = set()

        for idx, rec in enumerate(records):
            cid = rec.get("case_id")
            if not cid:
                reasons.append(f"Record {idx} missing case_id")
                continue
            if cid in seen_ids:
                reasons.append(f"Duplicate case_id {cid} at record {idx}")
            seen_ids.add(cid)

            origin = rec.get("evaluation_origin", "unknown")
            origins.add(origin)

            at = rec.get("attack_type")
            if at not in by_attack:
                reasons.append(f"Invalid attack type {at!r} in record {cid}")
                continue

            by_attack[at]["total"] += 1
            is_valid = rec.get("is_valid", True)
            if not is_valid:
                by_attack[at]["invalid"] += 1
                if rec.get("error_type"):
                    by_attack[at]["error"] += 1
            else:
                if rec.get("is_attack_success") is True:
                    by_attack[at]["success"] += 1

            em = rec.get("evaluation_method")
            if em:
                eval_methods.add(em)
                if em == "llm_judge":
                    jm = rec.get("judge_metadata", {}).get("judge_model") if rec.get("judge_metadata") else None
                    if not jm:
                        reasons.append(f"Record {cid} evaluated by llm_judge without declaring judge_model")
                    else:
                        judge_models.add(jm)

        # Evidence class inflation check
        summary_path = self.result_dir / "summary.json"
        if summary_path.is_file():
            try:
                summary = json.loads(summary_path.read_text(encoding="utf-8"))
                if "smoke" in str(self.result_dir).lower() or "smoke" in summary.get("result_state", "").lower():
                    if summary.get("official_protocol") is True:
                        reasons.append("Evidence class violation: smoke artifact cannot claim official_protocol=True")
                if "aether_transformed" in origins and summary.get("official_protocol") is True:
                    reasons.append("Evidence class violation: transformed cases cannot claim official_protocol=True")
            except Exception as exc:
                reasons.append(f"Corrupt summary JSON: {exc}")

        total_cases = len(records)
        total_success = sum(v["success"] for v in by_attack.values())
        total_invalid = sum(v["invalid"] for v in by_attack.values())
        total_errors = sum(v["error"] for v in by_attack.values())
        overall_asr = total_success / (total_cases - total_invalid) if (total_cases - total_invalid) > 0 else 0.0

        metrics = {
            "total_cases": total_cases,
            "total_success": total_success,
            "total_invalid": total_invalid,
            "total_errors": total_errors,
            "overall_asr": overall_asr,
            "by_attack": by_attack,
            "evaluation_methods": list(sorted(eval_methods)),
            "judge_models": list(sorted(judge_models)),
            "origins": list(sorted(origins)),
        }

        passed = len(reasons) == 0
        return TAMASVerificationResult(
            passed=passed,
            reasons=tuple(reasons),
            metrics=metrics,
            artifact_hashes=artifact_hashes,
        )
