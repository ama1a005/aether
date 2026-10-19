"""Run the bounded 12-case live demo qualification and save executed evidence."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from demo.backend.live_service import run_live_pipeline, run_live_rescue
from demo.backend.model_runtime import preload_model
from demo.backend.repository import load_cases


def main() -> None:
    """Execute clean/attack for 12 cases plus rescue for successful attacks."""
    preload_model()
    records = []
    for case in load_cases():
        clean = run_live_pipeline(case.case_id, False)
        attack = run_live_pipeline(case.case_id, True)
        rescue = run_live_rescue(case.case_id) if clean["correct"] and not attack["correct"] else None
        records.append({"case_id": case.case_id, "clean": clean, "attack": attack, "rescue": rescue})
    successful = [row for row in records if row["clean"]["correct"] and not row["attack"]["correct"]]
    primary = successful[0]["case_id"] if successful else None
    output = {
        "qualification_id": "DEMO-LIVE-QWEN05-MCP-12",
        "utc_timestamp": datetime.now(timezone.utc).isoformat(),
        "case_count": len(records),
        "selection_rule": "first case in fixed DEMO-PAT-001..012 order with clean-correct and attacked-incorrect",
        "primary_case_id": primary,
        "accepted": primary is not None,
        "records": records,
    }
    path = Path("demo/artifacts/live/qualification.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(json.dumps({"path": str(path), "accepted": output["accepted"], "primary_case_id": primary}))
    if primary is None:
        raise SystemExit("qualification failed: no clean-correct/attacked-incorrect case")


if __name__ == "__main__":
    main()
