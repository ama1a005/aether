"""Static safety checks for the generated CORE-04 Kaggle notebook."""

import json
from pathlib import Path

from scripts.build_kaggle_core04_notebook import COMMIT, build


ROOT = Path(__file__).resolve().parents[2]


def test_core04_notebook_is_pinned_restart_safe_and_test_locked() -> None:
    notebook = build(); source = "".join("".join(cell["source"]) for cell in notebook["cells"])
    assert len(COMMIT) == 40 and COMMIT in source
    assert "device='cuda'" not in source and 'device="cuda"' not in source
    assert "core04/checkpoint.tar.gz" in source and "--checkpoint-repo" in source
    assert "api.create_repo" in source and "private=True" in source
    assert "scripts.verify_core04_validation_bundle" in source
    assert "test_gate" not in source or "test_gate closed" in source


def test_checked_in_notebook_matches_builder() -> None:
    path = ROOT / "notebooks/aether_qwen_core04_locked_validation.ipynb"
    assert json.loads(path.read_text(encoding="utf-8")) == build()


def test_every_core04_code_cell_compiles() -> None:
    for index, cell in enumerate(build()["cells"]):
        if cell["cell_type"] == "code":
            compile("".join(cell["source"]), f"core04-cell-{index}", "exec")
