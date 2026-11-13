"""Compilation tests for supporting-experiment notebooks."""

from scripts.build_kaggle_supporting_notebook import build


def test_supporting_notebooks_are_pinned_clean_and_verified() -> None:
    for kind in ("red_team", "agent_c", "sae"):
        notebook = build(kind, "b" * 40)
        source = "".join("".join(cell["source"]) for cell in notebook["cells"])
        assert "b" * 40 in source and "scripts.verify_external_bundle" in source
        for index, cell in enumerate(notebook["cells"]):
            if cell["cell_type"] == "code": compile("".join(cell["source"]), f"cell-{index}", "exec")
