"""Report assembler for TAMAS benchmark following Phase 1 contracts."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from benchmarks.nov19_tamas.case import (
    ATTACK_TYPES,
    CODE_LICENSE,
    DATA_LICENSE,
    OFFICIAL_COMMIT,
    OFFICIAL_REPOSITORY,
    TOTAL_RECORDS,
)
from benchmarks.nov19_tamas.verifier import TAMASVerificationResult

SCHEMA_VERSION = "aether.nov19.external_benchmark.v1"


def assemble_tamas_summary(
    verification: TAMASVerificationResult,
    output_path: Path | None = None,
    execution_kind: str = "native_official",
    is_pilot: bool = False,
    execution_blocked_reasons: list[str] | None = None,
) -> dict[str, Any]:
    """Assemble TAMAS summary strictly from verified artifacts or explicit blocker.

    Fail-closed: smoke and transformed runs cannot claim official_protocol=True.
    """
    is_blocked = execution_blocked_reasons is not None and len(execution_blocked_reasons) > 0
    executed = verification.passed and not is_blocked

    is_smoke = "smoke" in execution_kind.lower()
    is_transformed = "transformed" in execution_kind.lower()

    if executed and not is_smoke and not is_transformed:
        status = "PASSED"
        overall = "PASS"
        official_protocol = True
    elif is_blocked:
        status = "BLOCKED"
        overall = "BLOCKED"
        official_protocol = False
    elif is_smoke:
        status = "SMOKE_PASSED" if verification.passed else "SMOKE_FAILED"
        overall = "INCOMPLETE"
        official_protocol = False
    else:
        status = "FAILED"
        overall = "FAIL"
        official_protocol = False

    limitations = [
        "Evaluates multi-agent conversational adversarial robustness; does not test DCMG internal circuit discovery.",
        "Code is licensed under MIT; benchmark data is licensed under CDLA-Permissive-2.0.",
    ]
    if is_pilot:
        limitations.append("This run evaluated an official native pilot subset, not the full 300-case suite.")
    if is_smoke:
        limitations.append("This is an adapter smoke test verifying dataset structure only, not executed agent interaction.")
    if is_blocked:
        limitations.extend(execution_blocked_reasons or [])

    metrics = verification.metrics
    summary: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "benchmark": "TAMAS",
        "evidence_class": (
            "adapter_dataset_smoke" if is_smoke
            else "aether_transformed_subset" if is_transformed
            else "official_native_subset" if is_pilot
            else "official_native_execution"
        ),
        "execution_kind": execution_kind,
        "official_repository": OFFICIAL_REPOSITORY,
        "upstream_revision": OFFICIAL_COMMIT,
        "official_commit": OFFICIAL_COMMIT,
        "licenses": {"code": CODE_LICENSE, "data": DATA_LICENSE},
        "official_protocol": official_protocol,
        "is_pilot": is_pilot,
        "status": status,
        "overall": overall,
        "denominators": {
            "total_cases": metrics.get("total_cases", 0),
            "successes": metrics.get("total_success", 0),
            "invalid_cases": metrics.get("total_invalid", 0),
            "error_cases": metrics.get("total_errors", 0),
        },
        "overall_attack_success_rate": metrics.get("overall_asr", 0.0),
        "by_attack_type": metrics.get("by_attack", {}),
        "evaluation_methods": metrics.get("evaluation_methods", []),
        "judge_models": metrics.get("judge_models", []),
        "raw_artifacts": list(verification.artifact_hashes.keys()),
        "artifact_sha256": verification.artifact_hashes,
        "limitations": limitations,
        "verification_reasons": list(verification.reasons),
        "utc_timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if output_path is not None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    return summary
