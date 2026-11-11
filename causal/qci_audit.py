"""Prospective QCI development-audit planning and budget validation."""

from __future__ import annotations

from typing import Any


def build_audit_plan(
    verification: dict[str, Any],
    selection: dict[str, Any],
    qualification_rows: list[dict[str, Any]],
    protocol: dict[str, Any],
) -> dict[str, Any]:
    """Build the frozen audit plan only after verified discovery support."""
    if verification.get("overall") != "PASS":
        raise ValueError("QCI discovery evidence is not verified")
    if verification.get("next_gate") != "ELIGIBLE_TO_FREEZE_DEVELOPMENT_AUDIT":
        raise ValueError("QCI discovery did not authorize development audit")
    supported = verification.get("supported_candidates")
    if not isinstance(supported, list) or not supported:
        raise ValueError("QCI development audit requires supported candidates")
    selected_by_id = {
        f"{row['agent']}.{row['candidate_id']}": row for row in selection["selected"]
    }
    unknown = sorted(set(str(item) for item in supported) - set(selected_by_id))
    if unknown:
        raise ValueError(f"QCI support contains candidates outside frozen selection: {unknown}")
    ranked = sorted(
        (selected_by_id[str(item)] for item in supported),
        key=lambda row: (
            -float(row["aggregate_score"]),
            f"{row['agent']}.{row['candidate_id']}",
        ),
    )
    maximum = int(protocol["candidate_policy"]["maximum_candidates"])
    candidates = ranked[:maximum]
    by_id = {str(row["case_id"]): row for row in qualification_rows}
    case_ids = [str(case_id) for case_id in protocol["development_audit_case_ids"]]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("QCI audit case IDs are not unique")
    try:
        cases = [by_id[case_id] for case_id in case_ids]
    except KeyError as error:
        raise ValueError(f"QCI audit case is absent from qualification rows: {error}") from error
    if any(row.get("split") != "development" or row.get("eligible") is not True for row in cases):
        raise ValueError("QCI audit contains an ineligible or non-development case")
    if {str(row["direction"]) for row in cases} != {"A_TO_B", "B_TO_A"}:
        raise ValueError("QCI audit does not represent both attack directions")
    operator_count = len(protocol["operators_per_candidate_per_case"])
    candidate_executions = len(candidates) * len(cases) * operator_count
    message_executions = sum(int(value) for value in protocol["message_positive_controls"].values())
    budget = protocol["budget"]
    if candidate_executions > int(budget["maximum_candidate_intervention_executions"]):
        raise ValueError("QCI audit candidate execution budget is insufficient")
    if message_executions > int(budget["maximum_message_control_executions"]):
        raise ValueError("QCI audit message-control budget is insufficient")
    if candidate_executions + message_executions > int(budget["maximum_total_executions"]):
        raise ValueError("QCI audit total execution budget is insufficient")
    return {
        "protocol_version": protocol["protocol_version"],
        "candidate_ids": [f"{row['agent']}.{row['candidate_id']}" for row in candidates],
        "candidate_rows": candidates,
        "case_ids": case_ids,
        "candidate_execution_count": candidate_executions,
        "message_control_execution_count": message_executions,
        "total_execution_count": candidate_executions + message_executions,
        "excluded_supported_candidates": [
            f"{row['agent']}.{row['candidate_id']}" for row in ranked[maximum:]
        ],
        "validation_executions": 0,
        "test_executions": 0,
    }
