"""
AETHER Shared Data Contracts — contracts/schemas.py
Version: 0.1.0
FROZEN — do not change field names or types without team approval + schema-change issue.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Literal, Optional
import json


# ---------------------------------------------------------------------------
# PatientCase
# ---------------------------------------------------------------------------

@dataclass
class PatientCase:
    """A structured experimental case derived from PTB-XL or synthetic fixtures."""
    case_id: str
    features: Dict[str, Any]               # structured ECG/vital metadata (not raw waveform)
    ground_truth_decision: str             # e.g. "ESCALATE" / "DO_NOT_ESCALATE"
    source_dataset: str = "fixture"        # "ptbxl" | "synthetic" | "fixture"
    source_split: str = "fixture"          # "fold_1"..."fold_10" | "fixture"
    ptbxl_fold: Optional[int] = None
    fixture_only: bool = False             # True = smoke test only, not paper results
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PatientCase":
        return cls(**d)


# ---------------------------------------------------------------------------
# A2AMessageRecord
# ---------------------------------------------------------------------------

@dataclass
class A2AMessageRecord:
    """A structured A2A message exchanged between agents."""
    message_id: str
    run_id: str
    sender: str
    receiver: str
    content_text: str
    structured_payload: Optional[Dict[str, Any]] = None
    token_ids_sender: Optional[List[int]] = None
    token_ids_receiver: Optional[List[int]] = None
    provenance: Dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "A2AMessageRecord":
        return cls(**d)


# ---------------------------------------------------------------------------
# AttackSpec
# ---------------------------------------------------------------------------

@dataclass
class AttackSpec:
    """Specification for one attack instance."""
    attack_id: str
    family: str                           # "tool_description_poison" | "tool_output_inject" | "a2a_manipulation"
    target_surface: str                   # "mcp_tool_description" | "mcp_tool_output" | "a2a_message"
    target_behavior: str                  # e.g. "DO_NOT_ESCALATE"  (attacker-desired decision)
    clean_payload: Any                    # benign tool description / output / message
    adversarial_payload: Any              # poisoned version
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "AttackSpec":
        return cls(**d)


# ---------------------------------------------------------------------------
# RunTrace
# ---------------------------------------------------------------------------

@dataclass
class RunTrace:
    """Complete execution trace for one agent run (clean or attacked)."""
    run_id: str
    case_id: str
    seed: int
    model_ids: Dict[str, str]             # {"agent_a": "<model_id>", "agent_b": "<model_id>"}
    messages: List[Dict[str, Any]]        # list of A2AMessageRecord dicts
    tool_calls: List[Dict[str, Any]]
    final_decision: str
    attack_id: Optional[str] = None
    decision_score: Optional[float] = None
    attack_success: bool = False
    artifact_paths: Dict[str, str] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "RunTrace":
        return cls(**d)


# ---------------------------------------------------------------------------
# ActivationTrace
# ---------------------------------------------------------------------------

@dataclass
class ActivationTrace:
    """Metadata for captured activations (tensors stored separately)."""
    run_id: str
    agent_id: str
    model_id: str
    component_granularity: str            # "layer" | "head" | "mlp_block"
    component_ids: List[str]              # e.g. ["L0", "L1.H3", ...]
    tensor_artifact_path: str             # path to .pt file
    token_map: Dict[str, Any]             # maps component_id -> token positions
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ActivationTrace":
        return cls(**d)


# ---------------------------------------------------------------------------
# InterventionSpec
# ---------------------------------------------------------------------------

@dataclass
class InterventionSpec:
    """Specification for one causal intervention."""
    intervention_id: str
    run_id: str
    location_type: Literal["sender", "message", "receiver"]
    component_id: str                     # e.g. "L3.H5" or "message_field:evidence"
    operator: str                         # "zero_ablation" | "mean_ablation" | "activation_patch"
    source_run_id: Optional[str] = None   # for patching: which run to copy from
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "InterventionSpec":
        return cls(**d)


# ---------------------------------------------------------------------------
# CircuitResult
# ---------------------------------------------------------------------------

@dataclass
class CircuitResult:
    """Result of a causal circuit discovery run."""
    experiment_id: str
    source_attack_ids: List[str]
    nodes: List[Dict[str, Any]]           # each node: {id, type, region, ...}
    edges: List[Dict[str, Any]]           # each edge: {src, dst, type, ...}
    faithfulness: float
    necessity: Optional[float]
    size: int                             # number of retained nodes
    benign_damage: float                  # benign utility loss under this circuit intervention
    search_method: str                    # "random" | "greedy" | "beam" | "rl"
    search_cost: Dict[str, Any]           # {"n_forward_passes": int, ...}
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CircuitResult":
        return cls(**d)
