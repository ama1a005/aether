"""MCPTox benchmark subsystem for AETHER Phase 1.

Implements native case mapping, official source hash validation,
preflight license auditing, deterministic subset selection,
faithful official-compatible evaluation, independent verification,
and report assembly for MCP tool-metadata poisoning.
"""

from benchmarks.nov19_mcptox.case import (
    MCPToxNativeCase,
    load_native_cases,
    select_predeclared_subset,
)
from benchmarks.nov19_mcptox.preflight import (
    MCPToxPreflightResult,
    run_mcptox_preflight,
)
from benchmarks.nov19_mcptox.evaluator import (
    MCPToxEvaluator,
    MCPToxEvaluationRecord,
    summarize_mcptox_outcomes,
)
from benchmarks.nov19_mcptox.verifier import (
    MCPToxArtifactVerifier,
    MCPToxVerificationResult,
)
from benchmarks.nov19_mcptox.report import assemble_mcptox_summary

__all__ = [
    "MCPToxNativeCase",
    "load_native_cases",
    "select_predeclared_subset",
    "MCPToxPreflightResult",
    "run_mcptox_preflight",
    "MCPToxEvaluator",
    "MCPToxEvaluationRecord",
    "summarize_mcptox_outcomes",
    "MCPToxArtifactVerifier",
    "MCPToxVerificationResult",
    "assemble_mcptox_summary",
]
