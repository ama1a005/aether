"""Report assembler for MCPTox benchmark following Phase 1 contracts."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from benchmarks.nov19_mcptox.case import (
    OFFICIAL_COMMIT,
    OFFICIAL_REPOSITORY,
    PURE_TOOL_SHA256,
    RESPONSE_SHA256,
    TOTAL_PINNED_CASES,
    TOTAL_PINNED_SERVERS,
)
from benchmarks.nov19_mcptox.verifier import MCPToxVerificationResult

SCHEMA_VERSION = "aether.nov19.external_benchmark.v1"


def assemble_mcptox_summary(
    verification: MCPToxVerificationResult,
    output_path: Path | None = None,
    execution_kind: str = "official_compatible",
    execution_blocked_reasons: list[str] | None = None,
) -> dict[str, Any]:
    """Assemble MCPTox summary strictly from verified artifacts or explicit blocker.

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
        overall = "INCOMPLETE"  # Smoke does not satisfy the official completion gate
        official_protocol = False
    else:
        status = "FAILED"
        overall = "FAIL"
        official_protocol = False

    limitations = [
        "Evaluates tool-metadata description poisoning; does not test DCMG causal circuit discovery.",
        "The pinned upstream repository lacks a LICENSE file; redistribution of raw cases is withheld pending legal resolution.",
        "The upstream publication abstract cites 1,312 cases and AAAI paper cites 1,348, whereas the pinned release contains exactly 485 records across 45 servers.",
    ]
    if is_smoke:
        limitations.append("This is released-response rescoring, not a fresh local Qwen2.5 execution.")
    if is_blocked:
        limitations.extend(execution_blocked_reasons or [])

    metrics = verification.metrics
    summary: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "benchmark": "MCPTox",
        "evidence_class": (
            "released_response_rescoring_smoke" if is_smoke
            else "aether_transformed_subset" if is_transformed
            else "official_compatible_tool_poisoning_evaluation"
        ),
        "execution_kind": execution_kind,
        "official_repository": OFFICIAL_REPOSITORY,
        "upstream_revision": OFFICIAL_COMMIT,
        "official_commit": OFFICIAL_COMMIT,
        "source_hashes": {
            "pure_tool.json": PURE_TOOL_SHA256,
            "response_all.json": RESPONSE_SHA256,
        },
        "pinned_release_geometry": {
            "servers": TOTAL_PINNED_SERVERS,
            "cases": TOTAL_PINNED_CASES,
        },
        "official_protocol": official_protocol,
        "status": status,
        "overall": overall,
        "denominators": {
            "total_cases": metrics.get("total_records", 0),
            "scored_cases": metrics.get("scored_records", 0),
            "none_cases": metrics.get("none_records", 0),
            "invalid_cases": metrics.get("N_invalid", 0),
            "error_cases": metrics.get("N_errors", 0),
            "successes": metrics.get("label_counts", {}).get("Success", 0),
        },
        "attack_success_rate": metrics.get("attack_success_rate", 0.0),
        "label_counts": metrics.get("label_counts", {}),
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
