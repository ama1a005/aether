"""Fail-closed planning and accounting for approved QCI-2 matched search."""

from __future__ import annotations

import hashlib
import itertools
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from causal.method_freeze import (
    load_and_validate_amendment,
    load_and_validate_proposal,
    sha256_file,
    validate_mask,
)


PROPOSAL_DECISION_SCHEMA = "aether.qci2-method-freeze-decision.v1"
AMENDMENT_DECISION_SCHEMA = "aether.qci2-method-freeze-amendment-decision.v1"
REQUIRED_METHODS = ("matched_random", "greedy", "beam", "receiver_only", "flat_ppo")


@dataclass(frozen=True)
class EffectiveMethodFreeze:
    """An approved proposal and amendment with their immutable byte hashes."""

    proposal: dict[str, Any]
    amendment: dict[str, Any]
    proposal_sha256: str
    amendment_sha256: str

    @property
    def effective_budget(self) -> dict[str, int]:
        """Return the v2 limits with v2.1 forward accounting applied."""
        base = self.proposal["matched_budget"]
        corrected = self.amendment["forward_accounting_correction"]
        return {
            "maximum_unique_search_masks": int(base["maximum_unique_search_masks"]),
            "maximum_total_mask_evaluations": int(base["maximum_total_mask_evaluations"]),
            "model_forwards_per_mask_evaluation": int(
                corrected["model_forwards_per_mask_evaluation"]
            ),
            "baseline_forward_steps": int(corrected["baseline_forward_steps"]),
            "maximum_model_forward_steps": int(corrected["maximum_model_forward_steps"]),
        }


@dataclass(frozen=True)
class MethodSeedPlan:
    """One isolated, reproducible matched-search work unit."""

    experiment_id: str
    method: str
    seed: int
    split: str
    case_ids: tuple[str, ...]
    cache_namespace: str
    proposal_sha256: str
    amendment_sha256: str
    maximum_unique_search_masks: int
    maximum_total_mask_evaluations: int
    model_forwards_per_mask_evaluation: int
    baseline_forward_steps: int
    maximum_model_forward_steps: int

    def to_dict(self) -> dict[str, Any]:
        """Serialize this plan without changing tuple order."""
        payload = asdict(self)
        payload["case_ids"] = list(self.case_ids)
        return payload


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected a JSON object: {path}")
    return value


def _validate_decision(
    path: Path,
    *,
    schema: str,
    hash_field: str,
    expected_hash: str,
) -> None:
    decision = _load_json(path)
    if decision.get("schema_version") != schema:
        raise ValueError(f"unsupported approval schema: {path}")
    if decision.get("decision_recorded") is not True or decision.get("decision") != "APPROVED":
        raise PermissionError(f"method is not approved: {path}")
    if decision.get("reviewer_role") != "human_project_owner":
        raise PermissionError(f"approval is not a human-owner decision: {path}")
    if decision.get(hash_field) != expected_hash:
        raise ValueError(f"approval hash differs from reviewed bytes: {path}")
    if decision.get("validation_executions") != 0 or decision.get("test_executions") != 0:
        raise PermissionError("approval record reports protected-split access")


def load_effective_method_freeze(
    *,
    repo: Path,
    proposal_path: Path,
    amendment_path: Path,
    proposal_decision_path: Path,
    amendment_decision_path: Path,
) -> EffectiveMethodFreeze:
    """Load the exact human-approved v2 + v2.1 method or fail before model access."""
    repo = repo.resolve()
    proposal_path = proposal_path.resolve()
    amendment_path = amendment_path.resolve()
    proposal = load_and_validate_proposal(proposal_path, repo)
    amendment = load_and_validate_amendment(amendment_path, proposal_path, repo)
    proposal_hash = sha256_file(proposal_path)
    amendment_hash = sha256_file(amendment_path)
    _validate_decision(
        proposal_decision_path.resolve(),
        schema=PROPOSAL_DECISION_SCHEMA,
        hash_field="proposal_sha256",
        expected_hash=proposal_hash,
    )
    _validate_decision(
        amendment_decision_path.resolve(),
        schema=AMENDMENT_DECISION_SCHEMA,
        hash_field="amendment_sha256",
        expected_hash=amendment_hash,
    )
    if amendment["base_proposal_sha256"] != proposal_hash:
        raise ValueError("approved amendment does not apply to the approved proposal")
    return EffectiveMethodFreeze(proposal, amendment, proposal_hash, amendment_hash)


def enumerate_legal_masks(proposal: Mapping[str, Any]) -> tuple[tuple[str, ...], ...]:
    """Enumerate every legal node mask in deterministic order, including empty."""
    nodes = sorted(
        row["id"] for row in proposal["candidate_graph"]["nodes"] if row["intervenable"]
    )
    masks: list[tuple[str, ...]] = []
    for count in range(len(nodes) + 1):
        for candidate in itertools.combinations(nodes, count):
            try:
                ordered = validate_mask(proposal, candidate)
            except ValueError as exc:
                if "overlapping interventions" in str(exc):
                    continue
                raise
            masks.append(ordered)
    return tuple(sorted(set(masks), key=lambda mask: (len(mask), mask)))


def build_run_plans(
    freeze: EffectiveMethodFreeze,
    *,
    methods: Iterable[str] | None = None,
    seeds: Iterable[int] | None = None,
) -> tuple[MethodSeedPlan, ...]:
    """Build independent method/seed plans with non-shareable cache identities."""
    proposal = freeze.proposal
    declared = {row["id"]: row for row in proposal["methods"]}
    selected_methods = tuple(methods or REQUIRED_METHODS)
    selected_seeds = tuple(int(seed) for seed in (seeds or proposal["seeds"]))
    if not selected_methods or len(selected_methods) != len(set(selected_methods)):
        raise ValueError("methods must be unique and nonempty")
    if not selected_seeds or len(selected_seeds) != len(set(selected_seeds)):
        raise ValueError("seeds must be unique and nonempty")
    unknown = set(selected_methods) - set(declared)
    if unknown:
        raise ValueError(f"unknown method names: {sorted(unknown)}")
    if any(seed not in proposal["seeds"] for seed in selected_seeds):
        raise ValueError("requested seed is outside the frozen seed list")
    budget = freeze.effective_budget
    plans: list[MethodSeedPlan] = []
    for method in selected_methods:
        for seed in selected_seeds:
            identity = f"{freeze.proposal_sha256}:{freeze.amendment_sha256}:{method}:{seed}"
            namespace = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]
            plans.append(MethodSeedPlan(
                experiment_id=proposal["experiment_id"], method=method, seed=seed,
                split=proposal["split"], case_ids=tuple(proposal["case_ids"]),
                cache_namespace=f"{method}-{seed}-{namespace}",
                proposal_sha256=freeze.proposal_sha256,
                amendment_sha256=freeze.amendment_sha256,
                **budget,
            ))
    namespaces = [plan.cache_namespace for plan in plans]
    if len(namespaces) != len(set(namespaces)):
        raise AssertionError("method/seed cache namespaces must be independent")
    return tuple(plans)

