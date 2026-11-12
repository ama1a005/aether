"""Tests for fail-closed QCI-2 row-level checkpointing."""

from __future__ import annotations

import json

import pytest

from instrumentation.run_qwen_causal_semantic_interventions import _load_resume_rows


def test_resume_accepts_only_exact_unique_sequence_prefix(tmp_path) -> None:
    expected = [("sender.a", "case1", "paired_rescue"), ("sender.a", "case1", "paired_induction")]
    raw = tmp_path / "raw.jsonl"
    rows = [
        {"candidate_id": "sender.a", "case_id": "case1", "operator": "paired_rescue",
         "hook_cleanup": True, "model_forward_steps": 1},
        {"candidate_id": "sender.a", "case_id": "case1", "operator": "paired_induction",
         "hook_cleanup": True, "model_forward_steps": 1},
    ]
    raw.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    assert _load_resume_rows(raw, expected) == rows

    raw.write_text("\n".join(json.dumps(row) for row in reversed(rows)) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="exact frozen-sequence prefix"):
        _load_resume_rows(raw, expected)


def test_resume_rejects_duplicate_or_unclean_rows(tmp_path) -> None:
    expected = [("sender.a", "case1", "paired_rescue"), ("sender.a", "case1", "paired_induction")]
    raw = tmp_path / "raw.jsonl"
    row = {"candidate_id": "sender.a", "case_id": "case1", "operator": "paired_rescue",
           "hook_cleanup": True, "model_forward_steps": 1}
    raw.write_text(json.dumps(row) + "\n" + json.dumps(row) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        _load_resume_rows(raw, expected)
    row["hook_cleanup"] = False
    raw.write_text(json.dumps(row) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unclean"):
        _load_resume_rows(raw, expected)
