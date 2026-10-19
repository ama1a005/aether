"""Opt-in, model-free end-to-end review demo smoke."""

import os
from pathlib import Path
import pytest

from demo.backend.service import generate_replay


@pytest.mark.skipif(os.getenv("AETHER_RUN_DEMO_E2E") != "1", reason="opt-in demo artifact generation")
@pytest.mark.parametrize("case_id", ["DEMO-PAT-001", "DEMO-PAT-002"])
def test_demo_e2e(case_id: str, tmp_path: Path) -> None:
    replay = generate_replay(case_id, replay_root=tmp_path)
    assert replay["clean"]["correct"] is True
    assert replay["attacked"]["receiver"]["decision"] != replay["clean"]["receiver"]["decision"]
    assert replay["rescue"]["normalized_recovery"] == 1.0
