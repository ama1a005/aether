"""Report assembler for BFCL evaluation following Phase 1 contracts."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from benchmarks.nov19_bfcl.preflight import (
    ADAPTER_REGISTRY_NAME,
    PHASE1_CATEGORIES,
    PINNED_MODEL_ID,
    PINNED_MODEL_REVISION,
    PINNED_PACKAGE_VERSION,
)
from benchmarks.nov19_bfcl.verifier import VerificationResult

SCHEMA_VERSION = "aether.nov19.external_benchmark.v1"


def assemble_bfcl_summary(
    verification: VerificationResult,
    output_path: Path | None = None,
    execution_blocked_reasons: list[str] | None = None,
) -> dict[str, Any]:
    """Assemble official BFCL summary strictly from verified artifacts or explicit blocker.

    Fail-closed discipline: if verification did not pass or execution was blocked,
    it does NOT claim overall: PASS or official_evaluator: true.
    """
    is_blocked = execution_blocked_reasons is not None and len(execution_blocked_reasons) > 0
    executed = verification.passed and not is_blocked

    if executed:
        status = "PASSED"
        overall = "PASS"
        official_evaluator = True
    elif is_blocked:
        status = "BLOCKED"
        overall = "BLOCKED"
        official_evaluator = False
    else:
        status = "FAILED"
        overall = "FAIL"
        official_evaluator = False

    limitations = [
        "Evaluates benign tool-use competence only; does not alone demonstrate DCMG novelty.",
        "Uses disclosed AETHER Qwen2.5 adapter; not an unmodified leaderboard submission.",
    ]
    if is_blocked:
        limitations.extend(execution_blocked_reasons or [])

    summary: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "benchmark": "BFCL",
        "evidence_class": "official_evaluator_with_disclosed_aether_model_adapter",
        "upstream_package": f"bfcl_eval=={PINNED_PACKAGE_VERSION}",
        "upstream_revision": PINNED_PACKAGE_VERSION,
        "model_id": PINNED_MODEL_ID,
        "model_revision": PINNED_MODEL_REVISION,
        "registry_adapter": ADAPTER_REGISTRY_NAME,
        "custom_model_adapter_disclosed": True,
        "official_evaluator": official_evaluator,
        "official_evaluator_executed": executed,
        "categories": list(PHASE1_CATEGORIES),
        "selection_rule": "complete categories: simple, multiple, parallel, irrelevance; no outcome conditioning",
        "partial_evaluation": False,
        "status": status,
        "overall": overall,
        "denominators": {
            "eligible": verification.metrics.get("total_eligible", 0),
            "valid": verification.metrics.get("total_eligible", 0) - verification.metrics.get("total_errors", 0),
            "errors": verification.metrics.get("total_errors", 0),
            "successes": verification.metrics.get("total_success", 0),
        },
        "metrics": verification.metrics,
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
