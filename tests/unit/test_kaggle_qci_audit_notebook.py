"""Static safety checks for the generated QCI-A1 Kaggle notebook."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
NOTEBOOK = ROOT / "notebooks/aether_qwen_causal_audit_cpu.ipynb"


def _sources() -> list[str]:
    notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    assert notebook["nbformat"] == 4
    assert all(not cell.get("outputs") for cell in notebook["cells"] if cell["cell_type"] == "code")
    return ["".join(cell["source"]) for cell in notebook["cells"] if cell["cell_type"] == "code"]


def test_qci_audit_notebook_is_commit_pinned_and_cpu_only() -> None:
    combined = "\n".join(_sources())
    assert "8d5e5d3f30de0b3df2e443b31afca90073fa1d6e" in combined
    assert "torch==2.14.1" in combined
    assert "https://download.pytorch.org/whl/cpu" in combined
    assert "instrumentation.run_qwen_causal_audit" in combined
    assert "aether-qwen-qci-results.tar.gz" in combined
    assert "aether-qwen-qci-audit-results.tar.gz" in combined
    assert "verify_qci_audit_bundle.py" in combined


def test_qci_audit_notebook_orders_verification_before_model_access() -> None:
    sources = _sources()
    verification = next(index for index, source in enumerate(sources) if "discovery-verification" in source)
    preflight = next(index for index, source in enumerate(sources) if "audit-preflight" in source)
    snapshot = next(index for index, source in enumerate(sources) if "MODEL_SNAPSHOT_DOWNLOAD_STARTED" in source)
    execution = next(index for index, source in enumerate(sources) if "qwen-causal-audit" in source)
    assert verification < preflight < snapshot < execution


def test_qci_audit_notebook_does_not_invoke_locked_splits() -> None:
    combined = "\n".join(_sources())
    assert "--validation" not in combined
    assert "--test" not in combined
