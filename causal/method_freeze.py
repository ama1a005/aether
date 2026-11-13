"""Validation for the prospective QCI-2 core method-freeze proposal."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml


ALLOWED_SPLIT = "development_discovery"
FORBIDDEN_CASES = frozenset({"v2_case_010", "v2_case_011", "v2_case_022", "v2_case_023"})
REQUIRED_METHODS = frozenset({"matched_random", "greedy", "beam", "receiver_only", "flat_ppo"})
REQUIRED_REGIONS = frozenset({"sender", "message", "receiver", "outcome"})
SUPPORTED_INTERNALS = frozenset({
    "sender.module.L22.attention_output",
    "receiver.module.L22.attention_output",
    "receiver.head.L20.H5.pre_o_proj",
    "receiver.head.L22.H7.pre_o_proj",
})


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of one file without normalizing its bytes."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_and_validate_proposal(path: Path, repo: Path) -> dict[str, Any]:
    """Load a method proposal and fail closed on leakage or evidence drift."""
    proposal = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(proposal, dict):
        raise TypeError("method-freeze proposal must be a mapping")
    if proposal.get("schema_version") != "aether.qci2-method-freeze-proposal.v1":
        raise ValueError("unsupported method-freeze proposal schema")
    if proposal.get("status") != "AWAITING_HUMAN_REVIEW":
        raise ValueError("proposal is not awaiting an independent human review")
    if proposal.get("split") != ALLOWED_SPLIT:
        raise PermissionError("method-freeze proposal may use development discovery only")
    case_ids = tuple(proposal.get("case_ids", ()))
    if not case_ids or len(case_ids) != len(set(case_ids)):
        raise ValueError("proposal requires unique development case IDs")
    if FORBIDDEN_CASES.intersection(case_ids):
        raise PermissionError("QCI-2 audit cases cannot tune or select the method")
    if proposal.get("validation_case_ids") or proposal.get("test_case_ids"):
        raise PermissionError("validation and test must remain sealed")

    nodes = proposal.get("candidate_graph", {}).get("nodes", [])
    node_ids = [row.get("id") for row in nodes]
    if len(node_ids) != len(set(node_ids)) or any(not node for node in node_ids):
        raise ValueError("candidate graph node IDs must be unique and nonempty")
    internal_ids = {row["id"] for row in nodes if row.get("kind") == "internal"}
    if internal_ids != SUPPORTED_INTERNALS:
        raise ValueError("internal candidate set differs from verified QCI-2 support")
    regions = {row.get("region") for row in nodes}
    if not REQUIRED_REGIONS.issubset(regions):
        raise ValueError("candidate graph must span sender, message, receiver and outcome")
    for edge in proposal.get("candidate_graph", {}).get("edges", []):
        if edge.get("source") not in node_ids or edge.get("target") not in node_ids:
            raise ValueError("candidate edge refers to an unknown node")
        if edge.get("status") != "hypothesized":
            raise ValueError("method proposal cannot pre-label an edge as supported")

    methods = {row.get("id") for row in proposal.get("methods", [])}
    if not REQUIRED_METHODS.issubset(methods):
        raise ValueError("required matched search methods are missing")
    budget = proposal.get("matched_budget", {})
    if type(budget.get("maximum_unique_masks")) is not int or budget["maximum_unique_masks"] < 1:
        raise ValueError("maximum_unique_masks must be a positive integer")
    if type(budget.get("maximum_model_forward_steps")) is not int or budget["maximum_model_forward_steps"] < 1:
        raise ValueError("maximum_model_forward_steps must be a positive integer")
    if proposal.get("cache_policy") != "fresh_cache_per_method_and_seed":
        raise ValueError("search methods may not share a hidden query cache")

    evidence = proposal.get("evidence_inputs", {})
    for label, record in evidence.items():
        artifact = (repo / record["path"]).resolve()
        if repo.resolve() not in artifact.parents or not artifact.is_file():
            raise FileNotFoundError(f"missing or out-of-repository evidence input: {label}")
        if sha256_file(artifact) != record["sha256"]:
            raise ValueError(f"evidence input hash mismatch: {label}")
    return proposal


def proposal_sha256(path: Path) -> str:
    """Return the immutable byte hash to place in a human review record."""
    return sha256_file(path)


def main() -> None:
    """Validate the repository proposal and print its prospective review hash."""
    root = Path(__file__).resolve().parents[1]
    path = root / "configs/phase1_core/qci2_method_freeze_v1.yaml"
    proposal = load_and_validate_proposal(path, root)
    print(json.dumps({
        "status": proposal["status"],
        "schema_version": proposal["schema_version"],
        "proposal_sha256": proposal_sha256(path),
        "case_count": len(proposal["case_ids"]),
        "method_count": len(proposal["methods"]),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
