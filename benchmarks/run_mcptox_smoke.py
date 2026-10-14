"""Score a deterministic subset of released MCPTox responses with official labels."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from benchmarks.mcptox import (
    OFFICIAL_COMMIT,
    PURE_TOOL_SHA256,
    RESPONSE_SHA256,
    load_official_cases,
    summarize_official_labels,
)
from experiments.manifest import sha256_file

ROOT = Path(".cache/benchmarks/MCPTox-Benchmark")
MODEL_KEY = "Qwen3-8b-No-Think"


def main() -> None:
    """Create a provenance-complete smoke artifact without live-server execution."""
    pure_path = ROOT / "pure_tool.json"
    response_path = ROOT / "response_all.json"
    official_cases = load_official_cases(pure_path)
    if len(official_cases) != 485:
        raise ValueError("pinned MCPTox release count changed")
    responses = json.loads(response_path.read_text(encoding="utf-8"))
    rows = []
    labels = []
    for server_name in sorted(responses["servers"]):
        for index, instance in enumerate(responses["servers"][server_name]["malicious_instance"]):
            if instance.get("wrong_data") == 1:
                continue
            data = instance["datas"][0]
            label = data["label"][MODEL_KEY]
            labels.append(label)
            rows.append({"case_id": f"{server_name}:{index:03d}", "server_name": server_name, "query": data["query"], "poisoned_tool": instance["poisoned_tool"], "paradigm": instance["metadata"]["paradigm"], "security_risk": instance["metadata"]["security risk"], "evaluation_origin": "mcptox_official_compatible", "released_model_key": MODEL_KEY, "released_response": data["response"][MODEL_KEY], "official_label": label})
            if len(rows) == 20:
                break
        if len(rows) == 20:
            break
    output_dir = Path("results/phase1/mcptox/smoke")
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "result_state": "SMOKE",
        "evaluation_origin": "mcptox_official_compatible",
        "execution_kind": "released_response_rescoring_not_local_qwen_inference",
        "official_repository": "https://github.com/zhiqiangwang4/MCPTox-Benchmark",
        "official_commit": OFFICIAL_COMMIT,
        "publication": "MCPTox, AAAI 2026, DOI 10.1609/aaai.v40i42.40895",
        "repository_license": "NO_LICENSE_FILE_PRESENT_REQUIRES_HUMAN_REVIEW",
        "published_counts": {"arxiv_abstract": 1312, "aaai_paper": 1348},
        "pinned_release": {"servers": 45, "poisoned_tool_records": 485, "pure_tool_sha256": PURE_TOOL_SHA256, "response_all_sha256": RESPONSE_SHA256},
        "subset_selection": "first 20 non-wrong_data released response records by sorted server and native instance order; no outcome conditioning",
        "released_model_key": MODEL_KEY,
        "official_label_metrics": summarize_official_labels(labels),
        "clean_competence": "not measurable from this released poisoned-response subset",
        "redistribution": "raw released records excluded pending license resolution",
        "limitations": ["no live MCP server execution", "no local Qwen2.5-0.5B result", "official release provides labels but no evaluator implementation"],
        "utc_timestamp": datetime.now(timezone.utc).isoformat(),
    }
    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    manifest = {
        "manifest_version": "1.0.0",
        "result_state": "SMOKE",
        "evaluation_origin": "mcptox_official_compatible",
        "official_commit": OFFICIAL_COMMIT,
        "source_hashes": {"pure_tool.json": PURE_TOOL_SHA256, "response_all.json": RESPONSE_SHA256},
        "artifacts": {str(summary_path): sha256_file(summary_path)},
        "subset_ids": [row["case_id"] for row in rows],
        "raw_records_redistributed": False,
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
