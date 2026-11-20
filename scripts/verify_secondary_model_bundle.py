"""Independently verify an executed SmolLM2 qualification bundle."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from typing import Any
from experiments.manifest import sha256_file
from paired_trace.secondary_model_freeze import load_and_validate, verify_decision
from causal.remediation_freeze import frozen_text_hash_matches

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL = ROOT / "configs/model_qualification/smollm2_1_7b_second_model_freeze_v1.json"
DECISION = ROOT / "configs/model_qualification/smollm2_1_7b_second_model_decision_v1.json"

def verify(bundle: Path) -> dict[str, Any]:
    """Return a receipt or fail on an inconsistent bundle."""
    proposal = load_and_validate(PROPOSAL, ROOT); verify_decision(PROPOSAL, DECISION)
    if not bundle.is_dir() or bundle.is_symlink(): raise ValueError("bundle must be a real directory")
    required = set(proposal["required_artifacts"]) | {"activation_tensors.pt"}
    missing = sorted(name for name in required if not (bundle / name).is_file())
    if missing: raise FileNotFoundError(f"second-model bundle missing: {missing}")
    archive = json.loads((bundle / "archive_contents.json").read_text(encoding="utf-8"))
    actual = {p.relative_to(bundle).as_posix(): sha256_file(p) for p in sorted(bundle.rglob("*"))
              if p.is_file() and p.name != "archive_contents.json"}
    if archive != actual: raise ValueError("archive hash inventory differs")
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    for name, digest in manifest["artifact_hashes"].items():
        if sha256_file(bundle / name) != digest: raise ValueError(f"manifest hash mismatch: {name}")
    summary = json.loads((bundle / "summary.json").read_text(encoding="utf-8"))
    if not frozen_text_hash_matches(PROPOSAL, str(summary["proposal_sha256"])):
        raise ValueError("proposal hash differs")
    if not frozen_text_hash_matches(DECISION, str(summary["decision_sha256"])):
        raise ValueError("decision hash differs")
    if summary["model"] != proposal["model"]: raise ValueError("model identity differs")
    if summary["validation_executions"] or summary["test_executions"]: raise PermissionError("protected split accessed")
    behavior_ok = (summary["behavioral"]["mq_g1"]["overall"] == "PASS"
                   and summary["behavioral"]["mq_g2"] is not None
                   and summary["behavioral"]["mq_g2"]["overall"] == "PASS")
    expected = "PASS" if behavior_ok and summary["instrumentation"]["overall"] == "PASS" else "FAIL"
    if not behavior_ok and summary["instrumentation"]["overall"] != "NOT_RUN_BEHAVIORAL_FAIL":
        raise ValueError("instrumentation should be closed after behavioral failure")
    if summary["overall"] != expected: raise ValueError("combined decision differs")
    return {"schema_version": "aether.second-model-verification.v1", "overall": expected,
            "model_id": proposal["model"]["model_id"], "git_commit": summary["git_commit"],
            "file_count": len(actual), "bundle_sha256": sha256_file(bundle / "archive_contents.json")}

def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(); parser.add_argument("bundle", type=Path)
    print(json.dumps(verify(parser.parse_args().bundle), indent=2, sort_keys=True))
if __name__ == "__main__": main()
