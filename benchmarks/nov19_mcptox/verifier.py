"""Independent verifier for MCPTox evaluation outputs and provenance."""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from benchmarks.nov19_mcptox.case import OFFICIAL_COMMIT, PURE_TOOL_SHA256


@dataclass(frozen=True)
class MCPToxVerificationResult:
    """Outcome of MCPTox artifact verification."""
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


class MCPToxArtifactVerifier:
    """Audits MCPTox result directories for provenance, label integrity, and denominator fidelity."""

    def __init__(self, result_dir: Path) -> None:
        self.result_dir = Path(result_dir)

    def verify(self) -> MCPToxVerificationResult:
        reasons = []
        artifact_hashes: dict[str, str] = {}
        metrics: dict[str, Any] = {}

        if not self.result_dir.is_dir():
            return MCPToxVerificationResult(
                passed=False,
                reasons=(f"Result directory does not exist: {self.result_dir}",),
            )

        json_files = sorted(self.result_dir.glob("*.json"))
        if not json_files:
            return MCPToxVerificationResult(
                passed=False,
                reasons=(f"No JSON artifacts found in {self.result_dir}",),
            )

        for jf in json_files:
            artifact_hashes[jf.name] = sha256(jf.read_bytes()).hexdigest()

        # Check for records file (e.g. evaluation_records.json or rows.json)
        records_path = self.result_dir / "evaluation_records.json"
        if not records_path.is_file():
            records_path = self.result_dir / "rows.json"

        if not records_path.is_file():
            reasons.append(f"Missing per-case evaluation records in {self.result_dir}")
            return MCPToxVerificationResult(
                passed=False,
                reasons=tuple(reasons),
                artifact_hashes=artifact_hashes,
            )

        try:
            records = json.loads(records_path.read_text(encoding="utf-8"))
        except Exception as exc:
            return MCPToxVerificationResult(
                passed=False,
                reasons=(f"Unreadable evaluation records JSON: {exc}",),
                artifact_hashes=artifact_hashes,
            )

        if not isinstance(records, list) or not records:
            return MCPToxVerificationResult(
                passed=False,
                reasons=("Evaluation records must be a non-empty list",),
                artifact_hashes=artifact_hashes,
            )

        seen_ids = set()
        label_counts: dict[str, int] = {}
        origin_set = set()

        for idx, rec in enumerate(records):
            cid = rec.get("case_id")
            if not cid:
                reasons.append(f"Record {idx} missing case_id")
                continue
            if cid in seen_ids:
                reasons.append(f"Duplicate case_id {cid} at record {idx}")
            seen_ids.add(cid)

            origin = rec.get("evaluation_origin", "unknown")
            origin_set.add(origin)

            lbl = rec.get("label", rec.get("official_label"))
            if not lbl:
                reasons.append(f"Record {cid} missing label")
            else:
                label_counts[lbl] = label_counts.get(lbl, 0) + 1

        total = len(records)
        n_none = label_counts.get("None", 0)
        n_scored = total - n_none
        successes = label_counts.get("Success", 0)
        expected_asr = successes / n_scored if n_scored > 0 else 0.0

        metrics = {
            "total_records": total,
            "scored_records": n_scored,
            "none_records": n_none,
            "label_counts": label_counts,
            "attack_success_rate": expected_asr,
            "origins": list(sorted(origin_set)),
        }

        # Check summary file if present
        summary_path = self.result_dir / "summary.json"
        if summary_path.is_file():
            try:
                summary = json.loads(summary_path.read_text(encoding="utf-8"))
                # Check for evidence class inflation
                if "smoke" in str(self.result_dir).lower() or "smoke" in summary.get("result_state", "").lower():
                    if summary.get("official_protocol") is True:
                        reasons.append(
                            "Evidence class violation: smoke artifact cannot declare official_protocol=True"
                        )
                if "aether_transformed" in origin_set and summary.get("official_protocol") is True:
                    reasons.append(
                        "Evidence class violation: transformed records cannot declare official_protocol=True"
                    )
            except Exception as exc:
                reasons.append(f"Corrupt summary JSON: {exc}")

        passed = len(reasons) == 0
        return MCPToxVerificationResult(
            passed=passed,
            reasons=tuple(reasons),
            metrics=metrics,
            artifact_hashes=artifact_hashes,
        )
