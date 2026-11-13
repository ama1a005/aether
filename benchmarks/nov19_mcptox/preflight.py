"""Preflight verification for MCPTox source, hashes, licensing, and protocol readiness."""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Any

from benchmarks.nov19_mcptox.case import (
    OFFICIAL_COMMIT,
    OFFICIAL_REPOSITORY,
    PURE_TOOL_SHA256,
    RESPONSE_SHA256,
    TOTAL_PINNED_CASES,
    TOTAL_PINNED_SERVERS,
    load_native_cases,
)


@dataclass(frozen=True)
class MCPToxPreflightResult:
    """Preflight outcome for MCPTox benchmark."""
    passed: bool
    reasons: tuple[str, ...]
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "reasons": list(self.reasons),
            "details": self.details,
        }


def check_mcptox_sources(
    source_dir: Path,
    verify_hashes: bool = True,
) -> tuple[bool, list[str], dict[str, Any]]:
    """Validate presence and integrity of official MCPTox dataset files."""
    reasons = []
    details: dict[str, Any] = {
        "repository": OFFICIAL_REPOSITORY,
        "commit": OFFICIAL_COMMIT,
        "source_dir": str(source_dir),
    }

    if not source_dir.is_dir():
        reasons.append(f"MCPTox source directory not found: {source_dir}")
        return False, reasons, details

    pure_tool = source_dir / "pure_tool.json"
    if not pure_tool.is_file():
        reasons.append(f"pure_tool.json missing from {source_dir}")
    elif verify_hashes:
        digest = sha256(pure_tool.read_bytes()).hexdigest()
        details["pure_tool_sha256"] = digest
        if digest != PURE_TOOL_SHA256:
            reasons.append(
                f"pure_tool.json SHA256 mismatch: expected {PURE_TOOL_SHA256}, got {digest}"
            )
        else:
            try:
                cases = load_native_cases(pure_tool, verify_pinned_hash=False)
                details["loaded_cases"] = len(cases)
                if len(cases) != TOTAL_PINNED_CASES:
                    reasons.append(
                        f"Expected {TOTAL_PINNED_CASES} cases in pure_tool.json, loaded {len(cases)}"
                    )
            except Exception as exc:
                reasons.append(f"Failed to parse pure_tool.json: {exc}")

    response_file = source_dir / "response_all.json"
    if response_file.is_file() and verify_hashes:
        resp_digest = sha256(response_file.read_bytes()).hexdigest()
        details["response_all_sha256"] = resp_digest
        if resp_digest != RESPONSE_SHA256:
            reasons.append(
                f"response_all.json SHA256 mismatch: expected {RESPONSE_SHA256}, got {resp_digest}"
            )

    return len(reasons) == 0, reasons, details


def check_mcptox_license(source_dir: Path) -> tuple[bool, list[str], dict[str, Any]]:
    """Audit license file presence and warn on unlicensed upstream repository."""
    reasons = []
    details: dict[str, Any] = {}
    license_files = [
        source_dir / "LICENSE",
        source_dir / "LICENSE.txt",
        source_dir / "LICENSE.md",
    ]
    has_license = any(lf.is_file() for lf in license_files)
    if not has_license:
        details["license_status"] = "NO_LICENSE_FILE_PRESENT_REQUIRES_HUMAN_REVIEW"
        reasons.append(
            "Pinned upstream MCPTox repository lacks an explicit LICENSE file; "
            "redistribution of raw cases prohibited pending human legal determination."
        )
    else:
        details["license_status"] = "LICENSE_PRESENT"

    return len(reasons) == 0, reasons, details


def run_mcptox_preflight(
    source_dir: Path,
    verify_hashes: bool = True,
    enforce_license_check: bool = False,
) -> MCPToxPreflightResult:
    """Run all MCPTox preflight checks."""
    all_reasons = []
    all_details: dict[str, Any] = {}

    src_ok, src_reasons, src_details = check_mcptox_sources(
        source_dir=source_dir,
        verify_hashes=verify_hashes,
    )
    all_reasons.extend(src_reasons)
    all_details["sources"] = src_details

    lic_ok, lic_reasons, lic_details = check_mcptox_license(source_dir)
    all_details["license"] = lic_details
    if enforce_license_check and not lic_ok:
        all_reasons.extend(lic_reasons)
    elif not lic_ok:
        # In non-enforcing mode (e.g. local research execution without redistribution),
        # record as diagnostic limitation rather than hard block
        all_details["license_warning"] = lic_reasons

    passed = src_ok and (lic_ok if enforce_license_check else True)
    return MCPToxPreflightResult(
        passed=passed,
        reasons=tuple(all_reasons),
        details=all_details,
    )
