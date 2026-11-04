import json

import pytest

from benchmarks.result_import import import_official_results, write_summary


def test_import_retains_errors_in_denominator(tmp_path):
    source = tmp_path / "official.json"
    source.write_text(json.dumps({"results": [
        {"task_id": "a", "passed": True},
        {"task_id": "b", "error": "timeout"},
    ]}))
    rows = import_official_results(source, benchmark="AgentDojo", id_field="task_id",
                                    success_field="passed")
    summary = write_summary(rows, tmp_path / "summary.json")
    assert summary["total"] == 2
    assert summary["invalid"] == 1
    assert summary["success_rate_total"] == .5


def test_import_rejects_duplicate_or_ambiguous_rows(tmp_path):
    source = tmp_path / "official.json"
    source.write_text(json.dumps([{"id": "a", "ok": 1}]))
    with pytest.raises(ValueError, match="boolean"):
        import_official_results(source, benchmark="BFCL", id_field="id", success_field="ok")
