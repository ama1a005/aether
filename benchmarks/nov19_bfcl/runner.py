"""Execution orchestrator and dry-run planner for BFCL evaluation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Sequence

from benchmarks.native_runners import NativeBenchmarkPlan, bfcl_qwen25_plan
from benchmarks.nov19_bfcl.preflight import (
    BFCLPreflightResult,
    PHASE1_CATEGORIES,
    PINNED_MODEL_REVISION,
    PINNED_PACKAGE_VERSION,
    run_bfcl_preflight,
)


@dataclass(frozen=True)
class BFCLRunPlan:
    """Consolidated BFCL execution plan with preflight and native commands."""
    preflight: BFCLPreflightResult
    native_plan: NativeBenchmarkPlan | None
    output_dir: Path
    created_at_utc: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "preflight": self.preflight.to_dict(),
            "native_plan": asdict(self.native_plan) if self.native_plan else None,
            "output_dir": str(self.output_dir),
            "created_at_utc": self.created_at_utc,
        }


class BFCLRunner:
    """Manages BFCL preflight, dry-run planning, and gated execution."""

    def __init__(
        self,
        snapshot_manifest: Path,
        output_dir: Path,
        categories: Sequence[str] = PHASE1_CATEGORIES,
        package_version: str = PINNED_PACKAGE_VERSION,
        model_revision: str = PINNED_MODEL_REVISION,
        backend: str = "vllm",
        num_gpus: int = 1,
    ) -> None:
        self.snapshot_manifest = Path(snapshot_manifest)
        self.output_dir = Path(output_dir)
        self.categories = tuple(categories)
        self.package_version = package_version
        self.model_revision = model_revision
        self.backend = backend
        self.num_gpus = num_gpus

    def plan(self, verify_snapshot_hashes: bool = True) -> BFCLRunPlan:
        """Construct the dry-run execution plan and assess readiness."""
        preflight = run_bfcl_preflight(
            manifest_path=self.snapshot_manifest,
            categories=self.categories,
            backend=self.backend,
            num_gpus=self.num_gpus,
            verify_snapshot_hashes=verify_snapshot_hashes,
        )

        native_plan = None
        try:
            native_plan = bfcl_qwen25_plan(
                package_version=self.package_version,
                model_revision=self.model_revision,
                snapshot_manifest=self.snapshot_manifest,
                categories=self.categories,
                output_dir=self.output_dir,
                num_gpus=self.num_gpus,
                backend=self.backend,
            )
        except Exception:
            native_plan = None

        return BFCLRunPlan(
            preflight=preflight,
            native_plan=native_plan,
            output_dir=self.output_dir,
            created_at_utc=datetime.now(timezone.utc).isoformat(),
        )

    def dry_run(self, plan_path: Path | None = None) -> dict[str, Any]:
        """Perform dry-run without executing commands or touching models."""
        run_plan = self.plan(verify_snapshot_hashes=False)
        payload = run_plan.to_dict()
        if plan_path is not None:
            plan_path.parent.mkdir(parents=True, exist_ok=True)
            plan_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload

    def execute(self, record_dir: Path | None = None) -> dict[str, Any]:
        """Execute the official BFCL plan strictly if preflight passes."""
        run_plan = self.plan(verify_snapshot_hashes=True)
        if not run_plan.preflight.passed:
            reasons = "; ".join(run_plan.preflight.reasons)
            raise RuntimeError(
                f"BFCL execution blocked: preflight checks failed: {reasons}"
            )
        if run_plan.native_plan is None:
            raise RuntimeError("BFCL native execution plan could not be constructed")

        rec_dir = record_dir or (self.output_dir / "execution_logs")
        rec_dir.mkdir(parents=True, exist_ok=True)
        (rec_dir / "plan.json").write_text(
            json.dumps(run_plan.to_dict(), indent=2), encoding="utf-8"
        )

        records = []
        for index, command in enumerate(run_plan.native_plan.commands):
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
            )
            record = {
                "index": index,
                "command": list(command),
                "exit_code": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            }
            (rec_dir / f"command_{index}.json").write_text(
                json.dumps(record, indent=2), encoding="utf-8"
            )
            records.append(record)
            if completed.returncode != 0:
                raise RuntimeError(
                    f"BFCL command {index} ({command[0]}) failed with exit code "
                    f"{completed.returncode}; logs retained in {rec_dir}"
                )

        return {
            "status": "COMPLETED",
            "commands_executed": len(records),
            "record_dir": str(rec_dir),
            "output_dir": str(self.output_dir),
        }
