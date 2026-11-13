"""Network-free verification of the complete review-demo package."""

from scripts.verify_demo_package import verify


def test_demo_package_api_and_evidence_contracts() -> None:
    result = verify(require_frontend_build=False)
    assert result["overall"] == "PASS"
    assert result["case_count"] == 12 and result["phase1_gate_count"] == 22
    assert result["live_external_services_tested"] is False
