"""Freeze balanced-V2 design identities before real-model execution."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from experiments.manifest import sha256_file

OUTPUT = Path("data/causal_v2/freeze_manifest_v2_1.json")
FILES = (
    Path("paired_trace/balanced_v2.py"),
    Path("paired_trace/run_balanced_v2_baseline.py"),
    Path("paired_trace/schemas.py"),
    Path("paired_trace/run_foundation.py"),
    Path("causal/v2_classification.py"),
    Path("data/causal_v2/case_registry.json"),
    Path("data/causal_v2/control_mappings.json"),
    Path("configs/experiments/balanced_v2_redesign_v2_1.json"),
    Path("data/causal_v2/freeze_manifest.json"),
    Path("docs/BALANCED_SUBSTRATE_V2.md"),
    Path("docs/GENERATION_STEP_INTERVENTION.md"),
    Path("docs/QWEN_HEAD_INSTRUMENTATION.md"),
)


def main() -> None:
    """Write one immutable pre-experiment hash manifest and refuse replacement."""
    if OUTPUT.exists():
        raise FileExistsError(f"frozen manifest already exists: {OUTPUT}")
    payload = {
        "freeze_version": "balanced-v2.1-pre-causal-experiment-v1",
        "revision_reason": "left-pad variable-length decoder-only batches and restore verified V1 mediator evidence wording after failed behavioral smoke",
        "utc_timestamp": datetime.now(timezone.utc).isoformat(),
        "checkpoint_commit": "303e0d8",
        "scope": "development_only",
        "validation_test_accessed": False,
        "files": {str(path): sha256_file(path) for path in FILES},
    }
    OUTPUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
