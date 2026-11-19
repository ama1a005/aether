"""Static safety checks for the generated CORE-05 Kaggle notebook."""

import json
from pathlib import Path

from scripts.build_kaggle_core05_notebook import COMMIT, build


ROOT = Path(__file__).resolve().parents[2]


def test_core05_notebook_is_pinned_checkpointed_and_once_only() -> None:
    notebook = build(); source = "".join("".join(cell["source"]) for cell in notebook["cells"])
    assert len(COMMIT) == 40 and COMMIT in source
    assert "core05/checkpoint.tar.gz" in source and "--checkpoint-repo" in source
    assert "attempt_marker.json" in source and "marker['state']=='COMPLETE'" in source
    assert "experiments.phase1.core05_once_only_test" in source
    assert "scripts.verify_core05_test_bundle" in source
    assert "device='cuda'" not in source and 'device="cuda"' not in source
    marker_cell = "".join(notebook["cells"][4]["source"])
    download_cell = "".join(notebook["cells"][5]["source"])
    assert "--preflight-only" in marker_cell and "snapshot_download" not in marker_cell
    assert "snapshot_download" in download_cell


def test_every_core05_code_cell_compiles() -> None:
    for index, cell in enumerate(build()["cells"]):
        if cell["cell_type"] == "code":
            compile("".join(cell["source"]), f"core05-cell-{index}", "exec")


def test_checked_in_core05_notebook_matches_builder() -> None:
    path = ROOT / "notebooks/aether_qwen_core05_once_only_test.ipynb"
    assert json.loads(path.read_text(encoding="utf-8")) == build()
