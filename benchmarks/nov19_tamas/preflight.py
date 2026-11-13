"""Preflight verification for native TAMAS framework, providers, and dataset integrity."""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib.metadata import PackageNotFoundError, version
import os
from pathlib import Path
from typing import Any

from benchmarks.nov19_tamas.case import (
    ATTACK_TYPES,
    CODE_LICENSE,
    DATA_LICENSE,
    OFFICIAL_COMMIT,
    OFFICIAL_REPOSITORY,
    TOTAL_RECORDS,
    load_tamas_dataset,
)


@dataclass(frozen=True)
class TAMASPreflightResult:
    """Preflight outcome for native TAMAS execution."""
    passed: bool
    reasons: tuple[str, ...]
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "reasons": list(self.reasons),
            "details": self.details,
        }


def check_tamas_framework(
    required_framework: str = "autogen",
) -> tuple[bool, list[str], dict[str, Any]]:
    """Verify that the official multi-agent execution framework is installed."""
    reasons = []
    details: dict[str, Any] = {"framework": required_framework}

    if required_framework in {"autogen", "pyautogen"}:
        installed_name = None
        for pkg in ("autogen", "pyautogen", "autogen-agentchat"):
            try:
                ver = version(pkg)
                installed_name = pkg
                details["installed_package"] = pkg
                details["version"] = ver
                break
            except PackageNotFoundError:
                continue
        if installed_name is None:
            reasons.append(
                "Native TAMAS requires AutoGen framework (autogen / pyautogen), "
                "which is not installed in this environment"
            )
    elif required_framework == "crewai":
        try:
            ver = version("crewai")
            details["installed_package"] = "crewai"
            details["version"] = ver
        except PackageNotFoundError:
            reasons.append(
                "Native TAMAS requires CrewAI framework (crewai), "
                "which is not installed in this environment"
            )
    else:
        reasons.append(f"Unsupported multi-agent framework: {required_framework}")

    return len(reasons) == 0, reasons, details


def check_tamas_provider_access(
    provider: str = "ollama",
    api_key_env_var: str | None = None,
) -> tuple[bool, list[str], dict[str, Any]]:
    """Verify provider settings and credentials."""
    reasons = []
    details: dict[str, Any] = {"provider": provider}

    if provider == "ollama":
        ollama_host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        details["ollama_host"] = ollama_host
        # Note: In offline/sandbox, endpoint check is deferred
    elif provider in {"openai", "azure", "anthropic"}:
        var_name = api_key_env_var or f"{provider.upper()}_API_KEY"
        details["api_key_env_var"] = var_name
        has_key = bool(os.environ.get(var_name))
        details["credential_configured"] = has_key
        if not has_key:
            reasons.append(f"Provider {provider} requires credentials in {var_name}")
    else:
        reasons.append(f"Unknown or unsupported model provider: {provider}")

    return len(reasons) == 0, reasons, details


def check_tamas_dataset(
    data_root: Path,
) -> tuple[bool, list[str], dict[str, Any]]:
    """Validate presence and structure of native TAMAS dataset across all 6 attack types."""
    reasons = []
    details: dict[str, Any] = {
        "repository": OFFICIAL_REPOSITORY,
        "commit": OFFICIAL_COMMIT,
        "data_root": str(data_root),
    }

    if not data_root.is_dir():
        reasons.append(f"TAMAS data directory not found: {data_root}")
        return False, reasons, details

    for at in ATTACK_TYPES:
        p = data_root / at
        if not p.is_dir():
            reasons.append(f"Attack directory missing: {at}")

    if not reasons:
        try:
            cases = load_tamas_dataset(data_root)
            details["total_cases_loaded"] = len(cases)
            if len(cases) != TOTAL_RECORDS:
                reasons.append(
                    f"Expected {TOTAL_RECORDS} cases across 6 attacks, loaded {len(cases)}"
                )
        except Exception as exc:
            reasons.append(f"Failed to load TAMAS dataset: {exc}")

    return len(reasons) == 0, reasons, details


def run_tamas_preflight(
    data_root: Path,
    framework: str = "autogen",
    provider: str = "ollama",
    api_key_env_var: str | None = None,
    enforce_framework: bool = True,
) -> TAMASPreflightResult:
    """Run all TAMAS preflight checks."""
    all_reasons = []
    all_details: dict[str, Any] = {}

    ds_ok, ds_reasons, ds_details = check_tamas_dataset(data_root)
    all_reasons.extend(ds_reasons)
    all_details["dataset"] = ds_details

    fw_ok, fw_reasons, fw_details = check_tamas_framework(framework)
    all_details["framework"] = fw_details
    if enforce_framework and not fw_ok:
        all_reasons.extend(fw_reasons)

    prov_ok, prov_reasons, prov_details = check_tamas_provider_access(
        provider=provider,
        api_key_env_var=api_key_env_var,
    )
    all_details["provider"] = prov_details
    if not prov_ok:
        all_reasons.extend(prov_reasons)

    passed = ds_ok and (fw_ok if enforce_framework else True) and prov_ok
    return TAMASPreflightResult(
        passed=passed,
        reasons=tuple(all_reasons),
        details=all_details,
    )
