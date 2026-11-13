"""Native execution wrapper and trajectory orchestrator for TAMAS benchmark."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Sequence

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


@dataclass(frozen=True)
class TAMASTrajectoryRecord:
    """Execution trace and evaluation outcome for one TAMAS multi-agent interaction."""
    case_id: str
    attack_type: str
    scenario: str
    agent_messages: tuple[dict[str, str], ...]
    is_attack_success: bool | None
    is_valid: bool
    evaluation_method: str  # "deterministic" | "llm_judge"
    error_type: str | None = None
    judge_metadata: dict[str, Any] | None = None
    evaluation_origin: str = "tamas_native_official"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["agent_messages"] = list(self.agent_messages)
        return data


@dataclass(frozen=True)
class TAMASRunPlan:
    """Predeclared execution plan for TAMAS."""
    preflight: TAMASPreflightResult
    cohort_ids: tuple[str, ...]
    framework: str
    provider: str
    evaluation_method: str
    is_pilot: bool
    output_dir: Path
    created_at_utc: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "preflight": self.preflight.to_dict(),
            "cohort_ids": list(self.cohort_ids),
            "framework": self.framework,
            "provider": self.provider,
            "evaluation_method": self.evaluation_method,
            "is_pilot": self.is_pilot,
            "output_dir": str(self.output_dir),
            "created_at_utc": self.created_at_utc,
        }


class TAMASNativeRunner:
    """Orchestrates native TAMAS execution with multi-agent framework."""

    def __init__(
        self,
        data_root: Path,
        output_dir: Path,
        framework: str = "autogen",
        provider: str = "ollama",
        per_attack_count: int | None = None,
        seed: int = 42,
        evaluation_method: str = "deterministic",
        judge_model: str | None = None,
    ) -> None:
        self.data_root = Path(data_root)
        self.output_dir = Path(output_dir)
        self.framework = framework
        self.provider = provider
        self.per_attack_count = per_attack_count
        self.seed = seed
        self.evaluation_method = evaluation_method
        self.judge_model = judge_model

    def plan(self, enforce_framework: bool = False) -> TAMASRunPlan:
        """Construct the dry-run plan and validate preflight conditions."""
        preflight = run_tamas_preflight(
            data_root=self.data_root,
            framework=self.framework,
            provider=self.provider,
            enforce_framework=enforce_framework,
        )

        cohort_ids: list[str] = []
        if preflight.details.get("dataset", {}).get("total_cases_loaded"):
            try:
                cases = load_tamas_dataset(self.data_root)
                cohort = select_predeclared_tamas_cohort(
                    cases,
                    per_attack_count=self.per_attack_count,
                    seed=self.seed,
                )
                cohort_ids = [c.case_id for c in cohort]
            except Exception:
                cohort_ids = []

        is_pilot = self.per_attack_count is not None and self.per_attack_count < 50
        return TAMASRunPlan(
            preflight=preflight,
            cohort_ids=tuple(cohort_ids),
            framework=self.framework,
            provider=self.provider,
            evaluation_method=self.evaluation_method,
            is_pilot=is_pilot,
            output_dir=self.output_dir,
            created_at_utc=datetime.now(timezone.utc).isoformat(),
        )

    def dry_run(self, plan_path: Path | None = None) -> dict[str, Any]:
        """Perform dry-run planning and export plan JSON."""
        run_plan = self.plan(enforce_framework=False)
        payload = run_plan.to_dict()
        if plan_path is not None:
            plan_path = Path(plan_path)
            plan_path.parent.mkdir(parents=True, exist_ok=True)
            plan_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload
