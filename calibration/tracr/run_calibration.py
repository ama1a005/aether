"""Minimal known-structure calibration using pinned official Tracr."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import sys
import time

import jax.numpy as jnp
from tracr.compiler import compiling, lib, nodes, rasp_to_graph
from tracr.rasp import rasp


def _jsonable(value: object) -> object:
    if hasattr(value, "shape"):
        return {"shape": list(value.shape), "dtype": str(value.dtype)}
    return str(value)


def _apply_with_params(model: object, params: object, tokens: list[object]) -> list[object]:
    """Apply the compiled model with an explicit parameter tree and decode."""
    encoded = model.input_encoder.encode(tokens)
    output = model.forward(params, jnp.array([encoded]))
    decoded = model.output_encoder.decode(output.unembedded_output[0].tolist())
    if model.input_encoder.bos_token:
        decoded = [model.input_encoder.bos_token, *decoded[1:]]
    return list(decoded)


def _ablate_target(params: object, target: str) -> tuple[object, list[dict[str, object]]]:
    """Return a copied parameter tree with one exact compiled half-layer zeroed."""
    copied = {module: dict(values) for module, values in params.items()}
    matched = []
    for module, values in copied.items():
        if module == target or module.startswith(target + "/"):
            for name, value in values.items():
                matched.append({
                    "module": module,
                    "parameter": name,
                    "shape": list(value.shape),
                    "pre_ablation_l2": float(jnp.linalg.norm(value)),
                })
                values[name] = jnp.zeros_like(value)
    if not matched:
        raise ValueError(f"Tracr intervention target has no parameters: {target}")
    return copied, matched


def main() -> None:
    """Compile official reverse, compare exact outputs, and record exposed structure."""
    config_path = Path("calibration/tracr/config.json")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    program = lib.make_reverse(rasp.tokens)
    extracted = rasp_to_graph.extract_rasp_graph(program)
    graph_nodes = []
    for node_id, attributes in extracted.graph.nodes(data=True):
        expression = attributes[nodes.EXPR]
        graph_nodes.append(
            {
                "id": str(node_id),
                "name": expression.name,
                "type": type(expression).__name__,
            }
        )
    graph_edges = [[str(source), str(target)] for source, target in extracted.graph.edges()]

    started = time.perf_counter()
    model = compiling.compile_rasp_to_model(
        program,
        vocab=set(config["vocab"]),
        max_seq_len=config["max_seq_len"],
        compiler_bos=config["compiler_bos"],
    )
    inputs = [["BOS", 1, 2, 3], ["BOS", 4, 2, 1], ["BOS", 1, 4]]
    cases = []
    expected_by_input = {}
    structure = None
    for tokens in inputs:
        output = model.apply(tokens)
        expected = [tokens[0], *reversed(tokens[1:])]
        observed = list(output.decoded)
        if observed != expected:
            raise AssertionError(f"Tracr reverse mismatch: {tokens} -> {observed}, expected {expected}")
        cases.append({"input": tokens, "expected": expected, "observed": observed, "exact_match": True})
        expected_by_input[tuple(tokens)] = expected
        if structure is None:
            structure = {
                "residuals": [_jsonable(value) for value in output.residuals],
                "layer_outputs": [_jsonable(value) for value in output.layer_outputs],
                "attention_logits": [_jsonable(value) for value in output.attn_logits],
            }

    passive_params = {module: dict(values) for module, values in model.params.items()}
    passive_cases = []
    for tokens in inputs:
        observed = _apply_with_params(model, passive_params, tokens)
        expected = expected_by_input[tuple(tokens)]
        passive_cases.append({
            "input": tokens,
            "expected": expected,
            "observed": observed,
            "exact_match": observed == expected,
        })

    intervention_rows = []
    for target in config["intervention"]["targets"]:
        ablated, parameter_records = _ablate_target(model.params, target)
        for tokens in inputs:
            expected = expected_by_input[tuple(tokens)]
            observed = _apply_with_params(model, ablated, tokens)
            changed_positions = [
                index for index, (before, after) in enumerate(zip(expected, observed))
                if index > 0 and before != after
            ]
            intervention_rows.append({
                "target": target,
                "operator": config["intervention"]["operator"],
                "input": tokens,
                "expected": expected,
                "observed": observed,
                "exact_match": observed == expected,
                "changed_non_bos_positions": changed_positions,
                "parameter_tensors": parameter_records,
            })

    restored_cases = []
    for tokens in inputs:
        observed = _apply_with_params(model, model.params, tokens)
        expected = expected_by_input[tuple(tokens)]
        restored_cases.append({
            "input": tokens,
            "expected": expected,
            "observed": observed,
            "exact_match": observed == expected,
        })
    predicates = {
        "baseline_all_exact": all(row["exact_match"] for row in cases),
        "passive_all_exact": all(row["exact_match"] for row in passive_cases),
        "at_least_one_target_changes_non_bos_output": any(
            row["changed_non_bos_positions"] for row in intervention_rows
        ),
        "restored_all_exact": all(row["exact_match"] for row in restored_cases),
        "all_targets_executed": {
            row["target"] for row in intervention_rows
        } == set(config["intervention"]["targets"]),
    }
    overall = "PASS" if all(predicates.values()) else "FAIL"

    packages = {
        name: importlib.metadata.version(name)
        for name in ["tracr", "jax", "jaxlib", "dm-haiku", "chex", "numpy"]
    }
    environment_path = Path("calibration/tracr/environment.json")
    environment = {
        "python": sys.version,
        "executable": sys.executable,
        "platform": platform.platform(),
        "packages": packages,
    }
    environment_path.write_text(json.dumps(environment, indent=2), encoding="utf-8")
    result = {
        "experiment_id": "P0_mech_20261111_tracr_reverse_intervention_0",
        "utc_timestamp": datetime.now(timezone.utc).isoformat(),
        "source": config,
        "classification": "known-structure transformer calibration",
        "cases": cases,
        "compiler_graph": {
            "node_count": len(graph_nodes),
            "edge_count": len(graph_edges),
            "nodes": graph_nodes,
            "edges": graph_edges,
        },
        "observed_internal_structure": structure,
        "intervention": {
            "performed": True,
            "protocol": config["intervention"],
            "passive_cases": passive_cases,
            "rows": intervention_rows,
            "restored_cases": restored_cases,
            "predicates": predicates,
            "overall": overall,
        },
        "validation_executions": 0,
        "test_executions": 0,
        "timing_seconds": {"total": time.perf_counter() - started},
    }
    output_dir = Path("results/calibration/tracr")
    output_dir.mkdir(parents=True, exist_ok=True)
    result_path = output_dir / "summary.json"
    result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    manifest = {
        "manifest_version": "1.0.0",
        "experiment_id": result["experiment_id"],
        "utc_timestamp": datetime.now(timezone.utc).isoformat(),
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "source_revision": config["revision"],
        "config_path": str(config_path),
        "config_sha256": sha256(config_path.read_bytes()).hexdigest(),
        "result_path": str(result_path),
        "result_sha256": sha256(result_path.read_bytes()).hexdigest(),
        "environment_path": str(environment_path),
        "environment_sha256": sha256(environment_path.read_bytes()).hexdigest(),
        "inputs": inputs,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    if overall != "PASS":
        raise RuntimeError("Tracr known-structure intervention calibration failed")


if __name__ == "__main__":
    main()
