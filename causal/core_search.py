"""Fail-closed planning and accounting for approved QCI-2 matched search."""

from __future__ import annotations

import hashlib
import itertools
import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from causal.method_freeze import (
    BudgetExhausted,
    MatchedBudgetLedger,
    load_and_validate_proposal,
    load_and_validate_v2_2_amendment,
    load_and_validate_v2_3_amendment,
    sha256_file,
    validate_mask,
)
from discovery.budgeted import Evaluation


PROPOSAL_DECISION_SCHEMA = "aether.qci2-method-freeze-decision.v1"
AMENDMENT_DECISION_SCHEMA = "aether.qci2-method-freeze-amendment-decision.v2.2"
METHOD_AMENDMENT_DECISION_SCHEMA = "aether.qci2-method-freeze-amendment-decision.v2.3"
REQUIRED_METHODS = ("matched_random", "greedy", "beam", "receiver_only", "flat_ppo")


@dataclass(frozen=True)
class EffectiveMethodFreeze:
    """An approved proposal and amendment with their immutable byte hashes."""

    proposal: dict[str, Any]
    amendment: dict[str, Any]
    method_amendment: dict[str, Any]
    proposal_sha256: str
    amendment_sha256: str
    method_amendment_sha256: str

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


@dataclass(frozen=True)
class CoreSearchOutcome:
    """One constraint-safe method result backed only by measured evaluations."""

    method: str
    seed: int
    retained: tuple[str, ...]
    evaluation: Evaluation
    feasible: bool
    stop_reason: str
    records: tuple[tuple[tuple[str, ...], Evaluation], ...]
    ledger: dict[str, Any]


class LegalMaskSession:
    """A fresh method/seed cache enforcing approved masks and all three budgets."""

    def __init__(self, freeze: EffectiveMethodFreeze, plan: MethodSeedPlan,
                 evaluate: Any) -> None:
        self.freeze = freeze
        self.plan = plan
        self.evaluate = evaluate
        self.legal = frozenset(enumerate_legal_masks(freeze.proposal))
        self.cache: dict[tuple[str, ...], Evaluation] = {}
        self.ledger = MatchedBudgetLedger(
            plan.maximum_unique_search_masks,
            plan.maximum_total_mask_evaluations,
            plan.maximum_model_forward_steps,
        )
        self.ledger.consume(
            phase="baselines", mask=(), forward_steps=plan.baseline_forward_steps,
            mask_evaluation=False,
        )

    def query(self, mask: Iterable[str], *, phase: str) -> Evaluation:
        """Evaluate one legal mask once; cached revisits consume no model budget."""
        normalized = validate_mask(self.freeze.proposal, tuple(mask))
        if normalized not in self.legal:
            raise ValueError("search attempted a mask outside the frozen legal domain")
        if normalized in self.cache:
            return self.cache[normalized]
        self.ledger.consume(
            phase=phase, mask=normalized,
            forward_steps=self.plan.model_forwards_per_mask_evaluation,
            search_mask=phase in {"search", "ppo_training"},
        )
        measured = self.evaluate(normalized)
        if not isinstance(measured, Evaluation):
            raise TypeError("CORE-02 evaluator must return a measured Evaluation")
        if measured.forward_passes != self.plan.model_forwards_per_mask_evaluation:
            raise ValueError("evaluator forward count differs from approved accounting")
        self.cache[normalized] = measured
        return measured

    def feasible(self, value: Evaluation) -> bool:
        """Apply the frozen faithfulness and benign-damage limits."""
        objective = self.freeze.proposal["objective"]
        return (
            value.faithfulness >= float(objective["feasibility"]["minimum_faithfulness"])
            and value.benign_damage <= float(objective["feasibility"]["maximum_benign_damage"])
        )

    def rank(self, mask: tuple[str, ...]) -> tuple[Any, ...]:
        """Prefer feasible compact masks, then effect, damage and stable identity."""
        value = self.cache[mask]
        return (
            0 if self.feasible(value) else 1,
            len(mask), -value.faithfulness, value.benign_damage, mask,
        )

    def outcome(self, method: str, seed: int, stop_reason: str) -> CoreSearchOutcome:
        """Return the best observed mask and a complete actual-consumption ledger."""
        if not self.cache:
            raise RuntimeError("search produced no measured mask")
        best = min(self.cache, key=self.rank)
        ledger = {
            "state": self.ledger.state,
            "unique_search_masks": len(self.ledger.unique_search_masks),
            "mask_evaluations": self.ledger.mask_evaluations,
            "model_forward_steps": self.ledger.model_forward_steps,
            "phase_counts": dict(self.ledger.phase_counts),
            "maximum_unique_search_masks": self.ledger.maximum_unique_search_masks,
            "maximum_total_mask_evaluations": self.ledger.maximum_total_mask_evaluations,
            "maximum_model_forward_steps": self.ledger.maximum_model_forward_steps,
        }
        return CoreSearchOutcome(
            method, seed, best, self.cache[best], self.feasible(self.cache[best]),
            stop_reason, tuple(self.cache.items()), ledger,
        )


def _children(mask: tuple[str, ...], legal: frozenset[tuple[str, ...]]) -> tuple[tuple[str, ...], ...]:
    return tuple(sorted({
        tuple(node for node in mask if node != removed)
        for removed in mask
        if tuple(node for node in mask if node != removed) in legal
    }))


def run_constraint_safe_search(
    freeze: EffectiveMethodFreeze,
    plan: MethodSeedPlan,
    evaluate: Any,
) -> CoreSearchOutcome:
    """Run one approved search method without ever constructing an overlap mask."""
    session = LegalMaskSession(freeze, plan, evaluate)
    legal = session.legal
    method = plan.method
    stop = "search_complete"
    try:
        if method == "matched_random":
            choices = sorted(legal)
            random.Random(plan.seed).shuffle(choices)
            for mask in choices[:plan.maximum_unique_search_masks]:
                session.query(mask, phase="search")
        elif method in {"greedy", "beam", "receiver_only"}:
            allowed = legal
            if method == "receiver_only":
                allowed = frozenset(mask for mask in legal if all(node.startswith("receiver.") for node in mask))
            maximal_size = max(map(len, allowed))
            frontier = sorted(mask for mask in allowed if len(mask) == maximal_size)
            width = 2 if method == "beam" else 1
            while frontier:
                for mask in frontier:
                    session.query(mask, phase="search")
                feasible = [mask for mask in frontier if session.feasible(session.cache[mask])]
                parents = sorted(feasible or frontier, key=session.rank)[:width]
                next_frontier = sorted({child for mask in parents for child in _children(mask, allowed)})
                if not next_frontier:
                    break
                frontier = next_frontier
        elif method == "flat_ppo":
            # The frozen flat baseline acts over the legal mask domain. Its
            # training actions are seeded and cache-aware; policy optimization
            # and checkpoint reload are handled by the execution runner.
            choices = sorted(legal)
            rng = random.Random(plan.seed)
            logits = {mask: 0.0 for mask in choices}
            for _ in range(256):
                unseen = [mask for mask in choices if mask not in session.cache]
                if unseen and len(session.cache) < plan.maximum_unique_search_masks:
                    mask = rng.choice(unseen)
                else:
                    mask = max(choices, key=lambda item: (logits[item], tuple(item)))
                value = session.query(mask, phase="ppo_training")
                reward = value.faithfulness - value.benign_damage - 0.1 * len(mask) / 6
                logits[mask] = 0.9 * logits[mask] + 0.1 * reward
        else:
            raise ValueError(f"unsupported approved method: {method}")
    except BudgetExhausted:
        stop = "INCOMPLETE_BUDGET"
    return session.outcome(method, plan.seed, stop)


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
    v2_1_amendment_path: Path,
    method_amendment_path: Path,
    proposal_decision_path: Path,
    amendment_decision_path: Path,
    method_amendment_decision_path: Path,
) -> EffectiveMethodFreeze:
    """Load the exact human-approved v2 + v2.1 method or fail before model access."""
    repo = repo.resolve()
    proposal_path = proposal_path.resolve()
    amendment_path = amendment_path.resolve()
    proposal = load_and_validate_proposal(proposal_path, repo)
    amendment = load_and_validate_v2_2_amendment(
        amendment_path, proposal_path, v2_1_amendment_path.resolve(), repo
    )
    method_amendment = load_and_validate_v2_3_amendment(
        method_amendment_path.resolve(), proposal_path, amendment_path,
        v2_1_amendment_path.resolve(), repo,
    )
    proposal_hash = sha256_file(proposal_path)
    amendment_hash = sha256_file(amendment_path)
    method_amendment_hash = sha256_file(method_amendment_path)
    _validate_decision(
        proposal_decision_path.resolve(),
        schema=PROPOSAL_DECISION_SCHEMA,
        hash_field="proposal_sha256",
        expected_hash=proposal_hash,
    )
    _validate_decision(
        method_amendment_decision_path.resolve(),
        schema=METHOD_AMENDMENT_DECISION_SCHEMA,
        hash_field="amendment_sha256",
        expected_hash=method_amendment_hash,
    )
    _validate_decision(
        amendment_decision_path.resolve(),
        schema=AMENDMENT_DECISION_SCHEMA,
        hash_field="amendment_sha256",
        expected_hash=amendment_hash,
    )
    if amendment["base_proposal_sha256"] != proposal_hash:
        raise ValueError("approved amendment does not apply to the approved proposal")
    return EffectiveMethodFreeze(
        proposal, amendment, method_amendment, proposal_hash, amendment_hash,
        method_amendment_hash,
    )


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

