"""Claim-safe demo tests for the verified causal-core evidence cards."""

from demo.backend.evidence import evidence_cards, system_status


def test_demo_exposes_verified_core_progression_without_deployment_claim() -> None:
    cards = {card["title"]: card for card in evidence_cards()}
    assert cards["CORE-03 Development Remediation"]["details"]["selected_arm"] == "mechanism_receiver_l20_h5"
    assert cards["CORE-04 Locked Validation"]["status"] == "VALIDATION_ACCEPTED"
    assert cards["CORE-05 Once-Only Test"]["status"] == "TEST_ACCEPTED"
    assert cards["CORE-05 Once-Only Test"]["details"]["oracle_dependent"] is True
    assert cards["CORE-05 Once-Only Test"]["details"]["repair_recovery_by_seed"] == [1.0, 1.0, 1.0]
    statuses = {row["capability"]: row["status"] for row in system_status()}
    assert statuses["Held-out validation"] == "VERIFIED ACCEPTED"
    assert statuses["Held-out test"] == "VERIFIED ACCEPTED — ONCE-ONLY CLOSED"
