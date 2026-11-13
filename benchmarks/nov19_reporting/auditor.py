"""Independent provenance auditor verifying raw artifacts against declared digests."""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AuditResult:
    """Outcome of provenance audit."""
    passed: bool
    reasons: tuple[str, ...]
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "reasons": list(self.reasons),
            "details": self.details,
        }


class BenchmarkProvenanceAuditor:
    """Audits handoffs and summaries against on-disk raw artifacts."""

    @staticmethod
    def audit_summary(summary_path: Path, base_dir: Path | None = None) -> AuditResult:
        summary_path = Path(summary_path)
        if not summary_path.is_file():
            return AuditResult(False, (f"Summary file not found: {summary_path}",))

        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except Exception as exc:
            return AuditResult(False, (f"Corrupt summary JSON: {exc}",))

        reasons = []
        details: dict[str, Any] = {"summary_file": str(summary_path)}

        # Check declared artifact hashes
        artifact_hashes = summary.get("artifact_sha256", {})
        if not isinstance(artifact_hashes, dict):
            reasons.append("artifact_sha256 must be a dictionary")
            return AuditResult(False, tuple(reasons), details)

        root = base_dir or summary_path.parent
        verified_count = 0
        details["checked_artifacts"] = {}

        for rel_path, expected_hash in artifact_hashes.items():
            target = root / rel_path
            if not target.is_file():
                # Also try checking if rel_path is absolute or directly inside root
                target = Path(rel_path)
                if not target.is_file():
                    reasons.append(f"Declared artifact missing from disk: {rel_path}")
                    continue

            actual_digest = sha256(target.read_bytes()).hexdigest()
            details["checked_artifacts"][rel_path] = actual_digest
            if actual_digest != expected_hash:
                reasons.append(
                    f"Digest mismatch for artifact {rel_path}: "
                    f"expected {expected_hash}, calculated {actual_digest}"
                )
            else:
                verified_count += 1

        details["verified_artifact_count"] = verified_count
        passed = len(reasons) == 0
        return AuditResult(passed=passed, reasons=tuple(reasons), details=details)
