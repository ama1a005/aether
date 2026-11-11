"""Audit Phase-1 completion against explicit, machine-readable evidence gates."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

import yaml

from scripts.verify_qci_audit_bundle import verify_audit
from scripts.verify_qci_bundle import verify


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs/phase1_completion_gates.yaml"


def _nested(value: Any, dotted: str) -> Any:
    """Read a dotted key from nested mappings and fail on absent structure."""
    current = value
    for part in dotted.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(dotted)
        current = current[part]
    return current


def _json_gate(path: Path, expected: dict[str, Any]) -> tuple[str, list[str]]:
    """Evaluate exact JSON predicates for one declared evidence artifact."""
    if not path.is_file():
        return "MISSING", [f"missing artifact: {path}"]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return "INVALID", [f"unreadable JSON: {type(error).__name__}: {error}"]
    failures = []
    for dotted, required in expected.items():
        try:
            observed = _nested(payload, dotted)
        except KeyError:
            failures.append(f"missing predicate: {dotted}")
            continue
        if observed != required:
            failures.append(f"{dotted}: expected {required!r}, observed {observed!r}")
    return ("PASS", []) if not failures else ("FAIL", failures)


def audit(repository: Path = ROOT, config_path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    """Return a complete gate-by-gate audit without treating absence as success."""
    repository = repository.resolve()
    config_path = config_path.resolve()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if config.get("schema_version") != "aether.phase1-completion.v1":
        raise ValueError("unsupported Phase-1 completion-gate schema")
    rows: list[dict[str, Any]] = []
    by_id: dict[str, dict[str, Any]] = {}
    for gate in config["gates"]:
        gate_id = str(gate["id"])
        if gate_id in by_id:
            raise ValueError(f"duplicate Phase-1 completion gate: {gate_id}")
        path = repository / str(gate["path"])
        kind = str(gate["kind"])
        details: dict[str, Any] = {}
        reasons: list[str] = []
        if kind == "json":
            status, reasons = _json_gate(path, dict(gate.get("expect", {})))
        elif kind == "qci_discovery":
            if not path.is_dir():
                status, reasons = "MISSING", [f"missing QCI discovery bundle: {path}"]
            else:
                try:
                    details = verify(path)
                    status = "PASS"
                except (OSError, KeyError, TypeError, ValueError) as error:
                    status, reasons = "INVALID", [f"QCI verification failed: {type(error).__name__}: {error}"]
        elif kind == "qci_audit_conditional":
            dependency = by_id.get(str(gate.get("depends_on")))
            if dependency is None:
                raise ValueError(f"QCI audit gate {gate_id} has an unresolved dependency")
            if dependency["status"] != "PASS":
                status, reasons = "BLOCKED", ["QCI discovery has not passed verification"]
            elif dependency["details"].get("next_gate") == "STOP_NO_SUPPORTED_CANDIDATE":
                status, reasons = "NOT_APPLICABLE", ["verified discovery found no supported internal candidate"]
            elif not path.is_dir():
                status, reasons = "MISSING", [f"missing required QCI audit bundle: {path}"]
            else:
                try:
                    details = verify_audit(path)
                    status = "PASS"
                except (OSError, KeyError, TypeError, ValueError) as error:
                    status, reasons = "INVALID", [f"QCI audit verification failed: {type(error).__name__}: {error}"]
        else:
            raise ValueError(f"unsupported Phase-1 gate kind: {kind}")
        row = {
            "id": gate_id,
            "category": str(gate["category"]),
            "kind": kind,
            "path": str(path),
            "status": status,
            "reasons": reasons,
            "details": details,
        }
        rows.append(row)
        by_id[gate_id] = row
    counts = Counter(row["status"] for row in rows)
    complete = all(row["status"] in {"PASS", "NOT_APPLICABLE"} for row in rows)
    return {
        "schema_version": config["schema_version"],
        "utc_timestamp": datetime.now(timezone.utc).isoformat(),
        "config_file": str(config_path),
        "overall": "PASS" if complete else "INCOMPLETE",
        "gate_count": len(rows),
        "status_counts": dict(sorted(counts.items())),
        "gates": rows,
        "claim_boundary": config["claim_boundary"],
    }


def main() -> None:
    """Print or save the audit and return nonzero while Phase 1 is incomplete."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", type=Path, default=ROOT)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    report = audit(arguments.repository, arguments.config)
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if arguments.output is not None:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    raise SystemExit(0 if report["overall"] == "PASS" else 1)


if __name__ == "__main__":
    main()
