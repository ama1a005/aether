"""TAMAS benchmark subsystem for AETHER Phase 1.

Implements native case mapping, CDLA-Permissive-2.0 data loading,
framework and provider preflight checks, native multi-agent execution orchestration,
LLM-judge vs deterministic evaluation distinction, independent verification,
and report assembly for multi-agent adversarial risks.
"""

from benchmarks.nov19_tamas.case import (
    ATTACK_TYPES,
    TAMASNativeCase,
    load_tamas_dataset,
    select_predeclared_tamas_cohort,
)
from benchmarks.nov19_tamas.preflight import (
    TAMASPreflightResult,
    run_tamas_preflight,
)
from benchmarks.nov19_tamas.runner import (
    TAMASNativeRunner,
    TAMASRunPlan,
    TAMASTrajectoryRecord,
)
from benchmarks.nov19_tamas.verifier import (
    TAMASArtifactVerifier,
    TAMASVerificationResult,
)
from benchmarks.nov19_tamas.report import assemble_tamas_summary

__all__ = [
    "ATTACK_TYPES",
    "TAMASNativeCase",
    "load_tamas_dataset",
    "select_predeclared_tamas_cohort",
    "TAMASPreflightResult",
    "run_tamas_preflight",
    "TAMASNativeRunner",
    "TAMASRunPlan",
    "TAMASTrajectoryRecord",
    "TAMASArtifactVerifier",
    "TAMASVerificationResult",
    "assemble_tamas_summary",
]
