"""Static safety checks for the generated CORE-03 Kaggle notebook."""

import json
from pathlib import Path

from scripts.build_kaggle_core03_notebook import COMMIT, build


ROOT = Path(__file__).resolve().parents[2]


def test_core03_notebook_is_pinned_restart_safe_and_cpu_frozen() -> None:
    notebook = build()
    source = "".join("".join(cell["source"]) for cell in notebook["cells"])
    assert len(COMMIT) == 40
    assert COMMIT in source
    assert "device='cuda'" not in source and 'device="cuda"' not in source
    assert "core03/checkpoint.tar.gz" in source
    assert "--checkpoint-repo" in source
    assert "scripts.verify_core03_remediation_bundle" in source
    assert "validation_case_ids" not in source
    assert "test_case_ids" not in source


def test_checked_in_notebook_matches_builder() -> None:
    path = ROOT / "notebooks/aether_qwen_core03_remediation.ipynb"
    assert json.loads(path.read_text(encoding="utf-8")) == build()
