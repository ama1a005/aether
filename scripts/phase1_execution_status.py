"""Validate and combine Phase-1 execution readiness with evidence status."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

from scripts.audit_phase1_completion import DEFAULT_CONFIG, ROOT, audit


DEFAULT_REGISTRY = ROOT / "configs/phase1_execution_registry.yaml"


def _safe_relative_path(value: str, repository: Path) -> Path:
    """Resolve a repository path and reject absolute or escaping paths."""
    candidate = Path(value)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"unsafe execution-registry path: {value}")
    resolved = (repository / candidate).resolve()
    try:
        resolved.relative_to(repository.resolve())
    except ValueError as error:
        raise ValueError(f"execution-registry path escapes repository: {value}") from error
    return resolved


def execution_status(
    repository: Path = ROOT,
    registry_path: Path = DEFAULT_REGISTRY,
    completion_config: Path = DEFAULT_CONFIG,
) -> dict[str, Any]:
    """Return a fail-closed dependency-aware execution status report."""
    repository = repository.resolve()
    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    if registry.get("schema_version") != "aether.phase1-execution.v1":
        raise ValueError("unsupported Phase-1 execution-registry schema")
    evidence = audit(repository, completion_config)
    evidence_by_id = {row["id"]: row for row in evidence["gates"]}
    stages = registry.get("stages")
    if not isinstance(stages, dict) or set(stages) != set(evidence_by_id):
        missing = sorted(set(evidence_by_id) - set(stages or {}))
        extra = sorted(set(stages or {}) - set(evidence_by_id))
        raise ValueError(f"execution registry must exactly cover completion gates; missing={missing}, extra={extra}")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(stage_id: str) -> None:
        if stage_id in visiting:
            raise ValueError(f"execution dependency cycle at {stage_id}")
        if stage_id in visited:
            return
        visiting.add(stage_id)
        dependencies = stages[stage_id].get("depends_on", [])
        if not isinstance(dependencies, list):
            raise ValueError(f"depends_on must be a list for {stage_id}")
        for dependency in dependencies:
            if dependency not in stages:
                raise ValueError(f"unknown dependency for {stage_id}: {dependency}")
            visit(dependency)
        visiting.remove(stage_id)
        visited.add(stage_id)

    for stage_id in stages:
        visit(stage_id)

    rows: list[dict[str, Any]] = []
    for stage_id, specification in stages.items():
        evidence_row = evidence_by_id[stage_id]
        dependencies = specification.get("depends_on", [])
        runner = specification.get("runner")
        runner_exists = None
        if runner is not None:
            runner_exists = _safe_relative_path(str(runner), repository).is_file()
            if not runner_exists:
                raise ValueError(f"declared runner does not exist for {stage_id}: {runner}")
        execution = str(specification.get("execution", ""))
        if evidence_row["status"] in {"PASS", "NOT_APPLICABLE"}:
            readiness = "COMPLETE"
        else:
            unmet = [item for item in dependencies if evidence_by_id[item]["status"] not in {"PASS", "NOT_APPLICABLE"}]
            if unmet:
                readiness = "BLOCKED_BY_DEPENDENCY"
            elif execution.startswith("blocked_"):
                readiness = "BLOCKED_BY_PROTOCOL_OR_RESOURCE"
            else:
                readiness = "READY_FOR_DECLARED_EXECUTION"
        rows.append({
            "id": stage_id,
            "category": evidence_row["category"],
            "evidence_status": evidence_row["status"],
            "readiness": readiness,
            "execution": execution,
            "depends_on": dependencies,
            "runner": runner,
            "runner_exists": runner_exists,
            "expected_artifact": str(Path(evidence_row["path"]).relative_to(repository)),
            "verification": specification.get("verification"),
            "reasons": evidence_row["reasons"],
        })
    return {
        "schema_version": registry["schema_version"],
        "overall_evidence": evidence["overall"],
        "claim_boundary": registry["claim_boundary"],
        "stages": rows,
    }


def main() -> None:
    """Print the combined status; incompleteness is reported, not an error."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", type=Path, default=ROOT)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--completion-config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    report = execution_status(arguments.repository, arguments.registry, arguments.completion_config)
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if arguments.output:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
