"""Validation for the prospective QCI-2 core method-freeze proposal."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

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
SUPPORTED_SCHEMAS = frozenset({
    "aether.qci2-method-freeze-proposal.v1",
    "aether.qci2-method-freeze-proposal.v2",
})
AMENDMENT_SCHEMA = "aether.qci2-method-freeze-amendment.v2.1"
AMENDMENT_V2_2_SCHEMA = "aether.qci2-method-freeze-amendment.v2.2"


class BudgetExhausted(RuntimeError):
    """The prospective method exhausted a declared accounting limit."""


@dataclass
class MatchedBudgetLedger:
    """Account for every method/seed phase without sharing evaluator caches."""

    maximum_unique_search_masks: int
    maximum_total_mask_evaluations: int
    maximum_model_forward_steps: int
    unique_search_masks: set[tuple[str, ...]] = field(default_factory=set)
    mask_evaluations: int = 0
    model_forward_steps: int = 0
    phase_counts: dict[str, int] = field(default_factory=dict)
    state: str = "RUNNING"

    def consume(self, *, phase: str, mask: Sequence[str], forward_steps: int,
                search_mask: bool = False, mask_evaluation: bool = True) -> None:
        """Record one real evaluator invocation or stop as incomplete."""
        if self.state != "RUNNING":
            raise BudgetExhausted("budget ledger is no longer running")
        if type(forward_steps) is not int or forward_steps < 0:
            raise ValueError("forward_steps must be a nonnegative integer")
        normalized = tuple(sorted(mask))
        prospective_unique = set(self.unique_search_masks)
        if search_mask:
            prospective_unique.add(normalized)
        evaluation_increment = int(mask_evaluation)
        if (len(prospective_unique) > self.maximum_unique_search_masks
                or self.mask_evaluations + evaluation_increment > self.maximum_total_mask_evaluations
                or self.model_forward_steps + forward_steps > self.maximum_model_forward_steps):
            self.state = "INCOMPLETE_BUDGET"
            raise BudgetExhausted("matched search budget exhausted")
        self.unique_search_masks = prospective_unique
        self.mask_evaluations += evaluation_increment
        self.model_forward_steps += forward_steps
        self.phase_counts[phase] = self.phase_counts.get(phase, 0) + 1

    def complete(self) -> None:
        """Mark a non-exhausted ledger complete."""
        if self.state != "RUNNING":
            raise BudgetExhausted("an incomplete ledger cannot be completed")
        self.state = "COMPLETE"


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
    if proposal.get("schema_version") not in SUPPORTED_SCHEMAS:
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

    if proposal["schema_version"].endswith(".v2"):
        _validate_v2(proposal)

    evidence = proposal.get("evidence_inputs", {})
    for label, record in evidence.items():
        artifact = (repo / record["path"]).resolve()
        if repo.resolve() not in artifact.parents or not artifact.is_file():
            raise FileNotFoundError(f"missing or out-of-repository evidence input: {label}")
        if sha256_file(artifact) != record["sha256"]:
            raise ValueError(f"evidence input hash mismatch: {label}")
    return proposal


def _validate_v2(proposal: Mapping[str, Any]) -> None:
    """Validate operational semantics introduced by the reviewed v2 correction."""
    semantics = proposal.get("mask_semantics", {})
    if semantics.get("mask_domain") != "intervenable_nodes_only":
        raise ValueError("search masks must contain intervenable nodes only")
    if semantics.get("nonselected_components") != "attacked_run_values_unchanged":
        raise ValueError("nonselected components must preserve attacked-run values")
    if semantics.get("application_order") != ["sender", "message", "receiver"]:
        raise ValueError("intervention application order must be sender, message, receiver")
    conflicts = {frozenset(row) for row in semantics.get("mutual_exclusion_groups", [])}
    required_conflicts = {
        frozenset({"message.decision_code", "message.whole"}),
        frozenset({"receiver.head.L22.H7.pre_o_proj", "receiver.module.L22.attention_output"}),
    }
    if not required_conflicts.issubset(conflicts):
        raise ValueError("required overlapping intervention exclusions are missing")
    edge_semantics = semantics.get("edge_semantics", {})
    if (edge_semantics.get("search_action") is not False
            or edge_semantics.get("promotion_requires") != "accepted_edge_specific_bvp_record"):
        raise ValueError("graph topology cannot act as or promote causal evidence")

    budget = proposal["matched_budget"]
    for name in ("maximum_unique_search_masks", "maximum_total_mask_evaluations",
                 "maximum_model_forward_steps", "model_forwards_per_mask_evaluation"):
        if type(budget.get(name)) is not int or budget[name] < 1:
            raise ValueError(f"{name} must be a positive integer")
    phases = budget.get("accounted_phases", [])
    required_phases = {"baselines", "negative_controls", "search", "ppo_training",
                       "checkpoint_reload", "independent_verification", "local_minimality"}
    if not required_phases.issubset(phases):
        raise ValueError("budget accounting omits a required phase")
    if budget.get("exhaustion_terminal_state") != "INCOMPLETE_BUDGET":
        raise ValueError("budget exhaustion must retain an incomplete run")

    benign = proposal.get("benign_noninterference", {})
    if (benign.get("metric") != "median_absolute_clean_logit_margin_change"
            or benign.get("units") != "raw_A_minus_B_logit_margin"
            or benign.get("maximum") != 0.1
            or benign.get("is_benign_utility") is not False):
        raise ValueError("benign non-interference metric or units differ")
    if not benign.get("separate_reports", {}).get("clean_decision_accuracy"):
        raise ValueError("clean decision accuracy must be reported separately")

    criteria = proposal.get("bvp_edge_acceptance", {})
    edge_ids = {row["id"] for row in proposal["candidate_graph"]["edges"]}
    if set(criteria) != edge_ids:
        raise ValueError("every hypothesized edge requires exact BVP acceptance criteria")
    for edge_id, rule in criteria.items():
        required = {"intervention", "downstream_measurement", "controls", "effect_direction",
                    "eligibility", "thresholds", "incoming_message_policy"}
        if not required.issubset(rule):
            raise ValueError(f"incomplete BVP rule: {edge_id}")

    stress = proposal.get("construct_validity", {}).get("separate_stress_protocol")
    if not stress or stress.get("status") != "PROSPECTIVE_NOT_EXECUTED":
        raise ValueError("a separate prospective construct-validity protocol is required")


def validate_mask(proposal: Mapping[str, Any], retained: Sequence[str]) -> tuple[str, ...]:
    """Validate a v2 node mask and return its deterministic application order."""
    if proposal.get("schema_version") != "aether.qci2-method-freeze-proposal.v2":
        raise ValueError("operational masks require the v2 proposal")
    nodes = {row["id"]: row for row in proposal["candidate_graph"]["nodes"]}
    if len(retained) != len(set(retained)):
        raise ValueError("mask contains duplicate nodes")
    unknown = set(retained) - set(nodes)
    if unknown:
        raise ValueError(f"mask contains unknown nodes: {sorted(unknown)}")
    if any(not nodes[node].get("intervenable") for node in retained):
        raise ValueError("outcome or other non-intervenable nodes cannot enter a search mask")
    for group in proposal["mask_semantics"]["mutual_exclusion_groups"]:
        if set(group).issubset(retained):
            raise ValueError(f"mask contains overlapping interventions: {group}")
    region_order = {name: index for index, name in enumerate(
        proposal["mask_semantics"]["application_order"])}
    return tuple(sorted(retained, key=lambda node: (region_order[nodes[node]["region"]], node)))


def edge_record_is_acceptable(rule: Mapping[str, Any], record: Mapping[str, Any]) -> bool:
    """Return true only for an executed edge record satisfying frozen predicates."""
    if record.get("evidence_type") != "real_model_intervention":
        return False
    if record.get("incoming_message_policy") != rule["incoming_message_policy"]:
        return False
    if record.get("effect_direction") != rule["effect_direction"]:
        return False
    if not all(control in record.get("controls_passed", []) for control in rule["controls"]):
        return False
    if record.get("eligible_count", 0) <= 0 or record.get("invalid_or_error_count") != 0:
        return False
    thresholds = rule["thresholds"]
    return all(float(record.get(metric, float("-inf"))) >= float(value)
               for metric, value in thresholds.items())


def proposal_sha256(path: Path) -> str:
    """Return the immutable byte hash to place in a human review record."""
    return sha256_file(path)


def load_and_validate_amendment(path: Path, base_path: Path, repo: Path) -> dict[str, Any]:
    """Validate a narrow accounting amendment against an immutable v2 base."""
    amendment = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(amendment, dict) or amendment.get("schema_version") != AMENDMENT_SCHEMA:
        raise ValueError("unsupported method-freeze amendment schema")
    if amendment.get("status") != "AWAITING_HUMAN_REVIEW":
        raise ValueError("accounting amendment is not awaiting human review")
    base = load_and_validate_proposal(base_path, repo)
    if amendment.get("base_proposal_sha256") != sha256_file(base_path):
        raise ValueError("accounting amendment base proposal hash differs")
    if base.get("schema_version") != "aether.qci2-method-freeze-proposal.v2":
        raise ValueError("accounting amendment requires the v2 proposal")
    correction = amendment.get("forward_accounting_correction", {})
    expected = {
        "sender_autoregressive_steps_per_case": 4,
        "receiver_forward_steps_per_case": 1,
        "case_count": 16,
        "model_forwards_per_mask_evaluation": 80,
        "baseline_forward_steps": 160,
        "maximum_model_forward_steps": 3760,
    }
    if correction != expected:
        raise ValueError("accounting amendment does not match qualified execution arithmetic")
    if amendment.get("scientific_method_changes") != "none_accounting_only":
        raise ValueError("amendment may change accounting only")
    return amendment


def load_and_validate_v2_2_amendment(
    path: Path, base_path: Path, v2_1_path: Path, repo: Path
) -> dict[str, Any]:
    """Validate the two-condition accounting correction against immutable inputs."""
    amendment = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(amendment, dict) or amendment.get("schema_version") != AMENDMENT_V2_2_SCHEMA:
        raise ValueError("unsupported v2.2 method-freeze amendment schema")
    if amendment.get("status") != "AWAITING_HUMAN_REVIEW":
        raise ValueError("v2.2 accounting amendment is not awaiting human review")
    base = load_and_validate_proposal(base_path, repo)
    load_and_validate_amendment(v2_1_path, base_path, repo)
    if amendment.get("supersedes_amendment") != str(v2_1_path.relative_to(repo)).replace("\\", "/"):
        raise ValueError("v2.2 amendment does not supersede the exact v2.1 path")
    if amendment.get("base_proposal_sha256") != sha256_file(base_path):
        raise ValueError("v2.2 amendment base proposal hash differs")
    if base.get("schema_version") != "aether.qci2-method-freeze-proposal.v2":
        raise ValueError("v2.2 accounting amendment requires the v2 proposal")
    expected = {
        "sender_autoregressive_steps_per_case_condition": 4,
        "receiver_forward_steps_per_case_condition": 1,
        "conditions_per_mask_evaluation": 2,
        "case_count": 16,
        "model_forwards_per_mask_evaluation": 160,
        "baseline_forward_steps": 160,
        "maximum_model_forward_steps": 7360,
    }
    if amendment.get("forward_accounting_correction") != expected:
        raise ValueError("v2.2 accounting does not count attack and benign conditions")
    if amendment.get("scientific_method_changes") != "none_accounting_only":
        raise ValueError("v2.2 amendment may change accounting only")
    return amendment


def main() -> None:
    """Validate the repository proposal and print its prospective review hash."""
    root = Path(__file__).resolve().parents[1]
    path = root / "configs/phase1_core/qci2_method_freeze_v2.yaml"
    proposal = load_and_validate_proposal(path, root)
    amendment_path = root / "configs/phase1_core/qci2_method_freeze_v2_1_amendment.yaml"
    amendment = load_and_validate_amendment(amendment_path, path, root)
    print(json.dumps({
        "status": proposal["status"],
        "schema_version": proposal["schema_version"],
        "proposal_sha256": proposal_sha256(path),
        "case_count": len(proposal["case_ids"]),
        "method_count": len(proposal["methods"]),
        "accounting_amendment_status": amendment["status"],
        "accounting_amendment_sha256": proposal_sha256(amendment_path),
        "effective_maximum_model_forward_steps": amendment[
            "forward_accounting_correction"]["maximum_model_forward_steps"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
