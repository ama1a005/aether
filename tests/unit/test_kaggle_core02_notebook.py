"""Model-free checks for the uploadable CORE-02 notebook."""

from scripts.build_kaggle_core02_notebook import COMMIT, build


def test_core02_notebook_is_pinned_restart_safe_and_split_locked() -> None:
    notebook = build()
    source = "".join("".join(cell["source"]) for cell in notebook["cells"])
    assert len(COMMIT) == 40 and COMMIT in source
    assert "aether-core02-checkpoint.tar.gz" in source
    assert "--declared-budget','7360" in source
    assert "scripts.verify_qci2_matched_search_bundle" in source
    assert "development-audit" in source and "validation or test" in source
    assert all(cell.get("outputs", []) == [] for cell in notebook["cells"] if cell["cell_type"] == "code")
