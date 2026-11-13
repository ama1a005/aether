"""Model-free unit tests for unified reporting, Wilson confidence intervals, schema, and provenance auditing."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import pytest

from benchmarks.nov19_reporting.auditor import BenchmarkProvenanceAuditor
from benchmarks.nov19_reporting.builder import UnifiedBenchmarkReportBuilder
from benchmarks.nov19_reporting.schema import ExternalBenchmarkHandoff, SCHEMA_VERSION
from benchmarks.nov19_reporting.statistics import (
    calculate_binomial_confidence_interval,
    calculate_cluster_confidence_interval,
)


def test_wilson_confidence_interval_bounds():
    # 50 out of 100
    low, high = calculate_binomial_confidence_interval(50, 100, confidence=0.95)
    assert 0.0 < low < 0.5
    assert 0.5 < high < 1.0
    assert pytest.approx((low + high) / 2, 0.05) == 0.5

    # 0 out of 100 (non-zero width, bounded at 0)
    low_0, high_0 = calculate_binomial_confidence_interval(0, 100, confidence=0.95)
    assert low_0 == 0.0
    assert high_0 > 0.0

    # 100 out of 100 (bounded at 1)
    low_1, high_1 = calculate_binomial_confidence_interval(100, 100, confidence=0.95)
    assert low_1 < 1.0
    assert high_1 == 1.0

    # 0 total
    assert calculate_binomial_confidence_interval(0, 0) == (0.0, 0.0)

    # Invalid input
    with pytest.raises(ValueError):
        calculate_binomial_confidence_interval(110, 100)


def test_cluster_confidence_interval():
    cases = [
        {"server": "s1", "is_attack_success": True},
        {"server": "s1", "is_attack_success": True},
        {"server": "s2", "is_attack_success": False},
        {"server": "s2", "is_attack_success": False},
    ]
    res = calculate_cluster_confidence_interval(cases, cluster_key="server")
    assert res["n_clusters"] == 2
    assert res["cluster_adjusted_mean"] == 0.5
    assert res["ci_lower"] <= 0.5 <= res["ci_upper"]


def test_schema_validation_rejects_malformed_handoff():
    with pytest.raises(ValueError, match="Invalid status"):
        ExternalBenchmarkHandoff(
            benchmark="BFCL",
            evidence_class="test",
            upstream_revision="v1",
            model_revision="rev1",
            cohort="all",
            selection_rule="rule",
            official_evaluator_executed=False,
            status="INVALID_STATUS_VALUE",
            denominators={"eligible": 0, "invalid": 0, "errors": 0},
            raw_artifacts=[],
            artifact_sha256={},
            limitations=[],
        )

    with pytest.raises(ValueError, match="Missing required denominator fields"):
        ExternalBenchmarkHandoff(
            benchmark="BFCL",
            evidence_class="test",
            upstream_revision="v1",
            model_revision="rev1",
            cohort="all",
            selection_rule="rule",
            official_evaluator_executed=False,
            status="BLOCKED",
            denominators={"eligible": 0},  # missing invalid, errors
            raw_artifacts=[],
            artifact_sha256={},
            limitations=[],
        )


def test_builder_exports_csv_and_methodology(tmp_path):
    builder = UnifiedBenchmarkReportBuilder()
    bfcl_handoff = ExternalBenchmarkHandoff(
        benchmark="BFCL",
        evidence_class="official_evaluator_with_disclosed_aether_model_adapter",
        upstream_revision="2026.3.23",
        model_revision="989aa798",
        cohort=["simple", "multiple"],
        selection_rule="complete categories",
        official_evaluator_executed=False,
        status="BLOCKED",
        denominators={"eligible": 0, "invalid": 0, "errors": 0, "successes": 0},
        raw_artifacts=[],
        artifact_sha256={},
        limitations=["GPU required"],
    )
    builder.add_benchmark(bfcl_handoff)

    summary = builder.build_summary()
    assert summary["schema_version"] == SCHEMA_VERSION
    assert "BFCL" in summary["benchmarks"]

    csv_path = tmp_path / "benchmarks_table.csv"
    builder.export_csv_table(csv_path)
    assert csv_path.is_file()
    content = csv_path.read_text(encoding="utf-8")
    assert "Benchmark,Evaluation Task" in content
    assert "BFCL" in content

    methodology = builder.generate_methodology_paragraph()
    assert "Berkeley Function Calling Leaderboard" in methodology
    assert "MCPTox" in methodology
    assert "TAMAS" in methodology


def test_provenance_auditor_detects_tampering(tmp_path):
    art = tmp_path / "raw.json"
    art.write_bytes(b'{"valid": true}')
    art_hash = sha256(b'{"valid": true}').hexdigest()

    summary_file = tmp_path / "summary.json"
    summary_file.write_text(json.dumps({
        "artifact_sha256": {"raw.json": art_hash},
    }))

    res = BenchmarkProvenanceAuditor.audit_summary(summary_file, base_dir=tmp_path)
    assert res.passed
    assert res.details["verified_artifact_count"] == 1

    # Tamper with file
    art.write_bytes(b'{"valid": false}')
    res_tampered = BenchmarkProvenanceAuditor.audit_summary(summary_file, base_dir=tmp_path)
    assert not res_tampered.passed
    assert any("Digest mismatch" in r for r in res_tampered.reasons)
