"""Regression checks for non-redistributive external source audits."""
from pathlib import Path

import pytest

from scripts.audit_external_benchmark_source import audit


def test_mcptox_audit_requires_exact_clean_checkout(tmp_path: Path) -> None:
    """An arbitrary directory cannot be represented as the pinned MCPTox source."""
    with pytest.raises(Exception):
        audit("mcptox", tmp_path)
