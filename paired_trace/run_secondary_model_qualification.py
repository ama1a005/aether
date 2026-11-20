"""Execute the approved SmolLM2 behavioral and instrumentation qualification."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
from typing import Any

import torch

from experiments.manifest import sha256_file
from instrumentation.adapters import LlamaModelAdapter
from paired_trace import run_model_qualification as primary
from paired_trace.run_foundation import _receiver_prompt
from paired_trace.schemas import MediatorMessage
from paired_trace.secondary_model_freeze import load_and_validate, verify_decision

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL = ROOT / "configs/model_qualification/smollm2_1_7b_second_model_freeze_v1.json"
DECISION = ROOT / "configs/model_qualification/smollm2_1_7b_second_model_decision_v1.json"
REGISTRY = ROOT / "data/causal_v2/case_registry.json"
RUN_ID = "P0_target_20261119_smollm2_second_model_seed42"


def _write(path: Path, value: Any) -> None:
    """Write strict, deterministic JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False), encoding="utf-8")


def _clean_commit() -> str:
    """Return HEAD only when the evidence source is clean."""
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
                          capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, check=True,
                           capture_output=True, text=True).stdout.strip()
    if dirty:
        raise RuntimeError("second-model evidence requires a clean source commit")
    return head


def prepare(proposal_path: Path, output: Path, decision_path: Path = DECISION) -> tuple[dict[str, Any], Path, Path]:
    """Validate exact approval and derive primary-engine configuration."""
    proposal_path, decision_path = proposal_path.resolve(), decision_path.resolve()
    if not proposal_path.is_relative_to(ROOT):
        raise ValueError("second-model proposal must be committed inside the repository")
    preliminary = json.loads(proposal_path.read_text(encoding="utf-8"))
    if preliminary.get("schema_version") != "aether.second-model-qualification-freeze.v1":
        raise ValueError("second-model proposal is not the prospectively frozen schema")
    proposal = load_and_validate(proposal_path, ROOT)
    verify_decision(proposal_path, decision_path)
    execution, model = proposal["execution"], proposal["model"]
    output.mkdir(parents=True, exist_ok=True)
    candidate = output / "derived_candidate.json"
    _write(candidate, {
        "status": "frozen_for_authorized_campaign", "model_id": model["model_id"],
        "revision": model["revision"], "device": "cpu", "dtype": "float32",
        "quantized": False, "explicit_offload": False, "disk_offload": False,
        "low_cpu_mem_usage": True, "trust_remote_code": False,
        "local_files_only": True, "cpu_threads": execution["cpu_threads"],
    })
    gate = json.loads(primary.HW_PATH.read_text(encoding="utf-8"))
    gate["candidate_model_id"] = model["model_id"]
    gate["authorized_single_model_id"] = model["model_id"]
    gate["minimum_pre_access_available_physical_ram_gib"] = execution["minimum_preload_available_memory_gib"]
    gate["minimum_post_load_available_physical_ram_gib"] = execution["minimum_postload_available_memory_gib"]
    hardware = output / "derived_hardware_gate.json"
    _write(hardware, gate)
    return proposal, candidate, hardware


def _configure_primary(candidate: Path, hardware: Path) -> None:
    """Bind the unchanged behavioral evaluator to SmolLM2."""
    primary.MODEL_CONFIG_PATH = candidate
    primary.HW_PATH = hardware
    primary.EXPERIMENT_ID = "P0_target_20261119_smollm2_second_model"
    primary.RUN_ID = RUN_ID
    primary.Qwen2ModelAdapter = LlamaModelAdapter


def run_instrumentation(proposal: dict[str, Any], output: Path, cache: Path) -> dict[str, Any]:
    """Measure passive hooks and one real clean-donor activation intervention."""
    spec, model_spec = proposal["instrumentation_acceptance"], proposal["model"]
    rows = json.loads(REGISTRY.read_text(encoding="utf-8"))["cases"]
    by_id = {row["case_id"]: row for row in rows}
    selected = [by_id[case_id] for case_id in spec["selected_case_ids"]]
    if any(row["split"] != "development" for row in selected):
        raise PermissionError("instrumentation attempted protected-split access")
    adapter = LlamaModelAdapter(model_spec["model_id"], model_spec["revision"], cache,
                                dtype=torch.float32, device="cpu", local_files_only=True)
    adapter.load()
    if len(adapter.model.model.layers) != model_spec["expected_layer_count"]:
        raise ValueError("loaded layer count differs from freeze")
    if int(adapter.model.config.hidden_size) != model_spec["expected_hidden_width"]:
        raise ValueError("loaded hidden width differs from freeze")
    adapter.tokenizer.padding_side = "left"
    sites = adapter.identify_components(spec["capture_layers"])
    tensors: dict[str, torch.Tensor] = {}
    records: list[dict[str, Any]] = []
    passive_ok = True
    for case in selected:
        message = MediatorMessage.from_sender_code(str(case["task_id"]), str(case["adversarial_code"]),
                                                   {"source": "second_model_gate"})
        inputs = adapter.tokenize([_receiver_prompt(adapter, message.serialize())])
        baseline = adapter.forward(inputs).logits.detach().cpu()
        adapter.install_comprehensive_capture(sites, [spec["head_capture_layer"]])
        hooked = adapter.forward(inputs).logits.detach().cpu()
        captured = {**adapter.activations, **adapter.head_activations}
        adapter.remove_hooks()
        passive_ok &= torch.allclose(baseline, hooked, rtol=spec["passive_logit_rtol"],
                                     atol=spec["passive_logit_atol"])
        for name, tensor in captured.items():
            tensors[f"{case['case_id']}::{name}"] = tensor
            records.append({"case_id": case["case_id"], "component": name,
                            "shape": list(tensor.shape),
                            "sha256": hashlib.sha256(tensor.numpy().tobytes()).hexdigest()})
    tensor_path = output / "activation_tensors.pt"
    torch.save(tensors, tensor_path)
    restored = torch.load(tensor_path, map_location="cpu", weights_only=True)
    round_trip = set(restored) == set(tensors) and all(torch.equal(restored[k], tensors[k]) for k in tensors)
    interventions: list[dict[str, Any]] = []
    for case_id in spec["intervention_case_ids"]:
        case = by_id[case_id]
        site = next(s for s in sites if s.layer == spec["intervention_layer"]
                    and s.component_type == spec["intervention_component_type"])
        messages = [MediatorMessage.from_sender_code(str(case["task_id"]), str(code),
                    {"source": "second_model_gate"}) for code in
                    (case["ground_truth_code"], case["adversarial_code"])]
        clean, attacked = [adapter.tokenize([_receiver_prompt(adapter, m.serialize())]) for m in messages]
        adapter.install_capture_hooks([site]); adapter.forward(clean)
        donor = adapter.activations[site.component_id]; adapter.remove_hooks()
        baseline = adapter.forward(attacked).logits.detach().cpu()
        if spec["intervention_token_position"] != -1:
            raise ValueError("approved second-model intervention requires the last token")
        adapter.install_last_token_patch(site, donor[:, -1, :])
        patched = adapter.forward(attacked).logits.detach().cpu()
        applications = adapter.intervention_applications; adapter.remove_hooks()
        interventions.append({"case_id": case_id, "component": site.component_id,
                              "token_position": spec["intervention_token_position"],
                              "applications": applications,
                              "maximum_absolute_logit_effect": float((patched - baseline).abs().max())})
    effect_ok = all(row["applications"] == 1 and row["maximum_absolute_logit_effect"] > 0
                    for row in interventions)
    cleanup_ok = not adapter._handles
    summary = {"schema_version": "aether.second-model-instrumentation.v1",
               "passive_non_interference": bool(passive_ok),
               "activation_round_trip": bool(round_trip), "intervention_effect": effect_ok,
               "hook_cleanup": cleanup_ok, "validation_executions": 0, "test_executions": 0}
    summary["overall"] = "PASS" if all((passive_ok, round_trip, effect_ok, cleanup_ok)) else "FAIL"
    _write(output / "activation_artifacts.json", {"captures": records, "interventions": interventions})
    _write(output / "instrumentation_summary.json", summary)
    return summary


def finalize(output: Path, proposal: dict[str, Any], instrumentation: dict[str, Any]) -> dict[str, Any]:
    """Create the combined result and reproducibility manifest."""
    behavioral = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    rows = json.loads((output / "mq_g1_rows.json").read_text(encoding="utf-8"))
    with (output / "raw_behavioral_rows.jsonl").open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
    _write(output / "behavioral_summary.json", {
        "mq_g1": behavioral["mq_g1"], "mq_g2": behavioral["mq_g2"],
        "overall": "PASS" if behavioral["mq_g1"]["overall"] == "PASS"
        and behavioral["mq_g2"]["overall"] == "PASS" else "FAIL",
    })
    behavior_ok = (behavioral["mq_g1"]["overall"] == "PASS"
                   and behavioral["mq_g2"] is not None
                   and behavioral["mq_g2"]["overall"] == "PASS")
    result = {"schema_version": "aether.second-model-qualification.v1", "run_id": RUN_ID,
              "utc_timestamp": datetime.now(timezone.utc).isoformat(), "git_commit": _clean_commit(),
              "model": proposal["model"], "proposal_sha256": sha256_file(PROPOSAL),
              "decision_sha256": sha256_file(DECISION), "behavioral": behavioral,
              "instrumentation": instrumentation,
              "overall": "PASS" if behavior_ok and instrumentation["overall"] == "PASS" else "FAIL",
              "validation_executions": 0, "test_executions": 0,
              "claim_boundary": proposal["claim_boundary"]}
    _write(output / "summary.json", result)
    required = [output / name for name in proposal["required_artifacts"]
                if name not in {"archive_contents.json", "manifest.json"}]
    missing = [path.name for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"required second-model artifacts missing: {missing}")
    manifest = {"schema_version": "aether.second-model-manifest.v1", "run_id": RUN_ID,
                "git_commit": result["git_commit"], "python": platform.python_version(),
                "command_line": sys.argv, "model_id": proposal["model"]["model_id"],
                "model_revision": proposal["model"]["revision"], "seed": proposal["execution"]["seed"],
                "dataset_hash": proposal["behavioral_qualification"]["cases_sha256"],
                "artifact_hashes": {path.name: sha256_file(path) for path in required}}
    _write(output / "manifest.json", manifest)
    hashes = {path.relative_to(output).as_posix(): sha256_file(path)
              for path in sorted(output.rglob("*")) if path.is_file() and path.name != "archive_contents.json"}
    _write(output / "archive_contents.json", hashes)
    return result


def main() -> None:
    """Run preflight or the approved complete qualification."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proposal", type=Path, default=PROPOSAL)
    parser.add_argument("--decision", type=Path, default=DECISION)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    proposal, candidate, hardware = prepare(args.proposal, args.output, args.decision)
    _configure_primary(candidate, hardware)
    delegated = [sys.argv[0], "--output", str(args.output), "--cache", str(args.cache)]
    if args.preflight_only:
        delegated.append("--preflight-only")
    sys.argv = delegated
    primary.main()
    if args.preflight_only:
        return
    behavioral = json.loads((args.output / "summary.json").read_text(encoding="utf-8"))
    if (behavioral["mq_g1"]["overall"] != "PASS" or behavioral["mq_g2"] is None
            or behavioral["mq_g2"]["overall"] != "PASS"):
        skipped = {"schema_version": "aether.second-model-instrumentation.v1",
                   "overall": "NOT_RUN_BEHAVIORAL_FAIL",
                   "reason": "stop_after_behavioral_failure",
                   "validation_executions": 0, "test_executions": 0}
        _write(args.output / "activation_artifacts.json", {"captures": [], "interventions": []})
        torch.save({}, args.output / "activation_tensors.pt")
        _write(args.output / "instrumentation_summary.json", skipped)
        result = finalize(args.output, proposal, skipped)
    else:
        result = finalize(args.output, proposal, run_instrumentation(proposal, args.output, args.cache))
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
