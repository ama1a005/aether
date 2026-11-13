"""Real Qwen evaluator for approved two-condition CORE-02 node masks."""

from __future__ import annotations

from statistics import median
from typing import Any, Mapping

import torch

from causal.method_freeze import validate_mask
from causal.qci_execution import QCICandidate, parse_candidate
from discovery.budgeted import Evaluation
from instrumentation.adapters import HeadPatch, ModulePatch, Qwen2ModelAdapter
from instrumentation.run_qwen_causal_interventions import (
    _capture_sources, _module_site, _prompt_and_ids, _qualified_inputs,
)
from paired_trace.metrics import validate_label_tokens


INTERNALS = {
    "sender.module.L22.attention_output": ("sender", "module.L22.attention_output"),
    "receiver.module.L22.attention_output": ("receiver", "module.L22.attention_output"),
    "receiver.head.L20.H5.pre_o_proj": ("receiver", "head.L20.H5.pre_o_proj"),
    "receiver.head.L22.H7.pre_o_proj": ("receiver", "head.L22.H7.pre_o_proj"),
}


def _candidate(address: str) -> QCICandidate:
    agent, identifier = INTERNALS[address]
    return parse_candidate({"agent": agent, "candidate_id": identifier,
                            "family": "head" if ".head." in address else "module"})


class QwenMatchedMaskEvaluator:
    """Execute attacked rescue and clean identity for every fixed discovery case."""

    def __init__(self, adapter: Qwen2ModelAdapter, proposal: Mapping[str, Any],
                 rows: list[dict[str, Any]]) -> None:
        self.adapter = adapter
        self.proposal = proposal
        by_id = {str(row["case_id"]): row for row in rows}
        self.rows = [by_id[case_id] for case_id in proposal["case_ids"]]
        if len(self.rows) != 16 or any(row.get("split") != "development" or not row.get("eligible") for row in self.rows):
            raise PermissionError("CORE-02 requires exactly 16 eligible development cases")
        self.label_ids = validate_label_tokens(adapter.tokenizer)
        self.candidates = {address: _candidate(address) for address in INTERNALS}
        self.sources: dict[tuple[str, str], dict[str, torch.Tensor]] = {}

    def capture_clean_sources(self) -> None:
        """Capture paired clean donors once; captures are not search evaluations."""
        for row in self.rows:
            for agent in ("sender", "receiver"):
                selected = [candidate for candidate in self.candidates.values() if candidate.agent == agent]
                prompt, ids = _prompt_and_ids(row, agent, "clean")
                inputs = _qualified_inputs(self.adapter, prompt, ids)
                self.sources[(str(row["case_id"]), agent)] = _capture_sources(
                    self.adapter, inputs, selected
                )

    def _install_internal_patches(self, case_id: str, addresses: list[str], *,
                                  sender: bool) -> None:
        modules: list[ModulePatch] = []
        heads: list[HeadPatch] = []
        for address in addresses:
            candidate = self.candidates[address]
            source = self.sources[(case_id, candidate.agent)][candidate.candidate_id]
            if candidate.family == "module":
                modules.append(ModulePatch(
                    address, _module_site(self.adapter, candidate), source,
                    token_position=-1, target_generation_step=0 if sender else None,
                ))
            else:
                heads.append(HeadPatch(
                    address, candidate.layer, int(candidate.head), source,
                    token_position=-1, target_generation_step=0 if sender else None,
                ))
        if modules or heads:
            self.adapter.install_multi_patch(module_patches=modules, head_patches=heads)

    def _condition(self, row: dict[str, Any], mask: tuple[str, ...],
                   condition: str) -> dict[str, Any]:
        case_id = str(row["case_id"])
        sender_nodes = [node for node in mask if node.startswith("sender.")]
        receiver_nodes = [node for node in mask if node.startswith("receiver.")]
        prompt, ids = _prompt_and_ids(row, "sender", condition)
        inputs = _qualified_inputs(self.adapter, prompt, ids)
        self.adapter.intervention_application_counts = {}
        try:
            self._install_internal_patches(case_id, sender_nodes, sender=True)
            generated = self.adapter.generate_uncached(inputs, 4)
            sender_counts = dict(self.adapter.intervention_application_counts)
        finally:
            self.adapter.remove_hooks()
        code = self.adapter.tokenizer.decode(
            [int(generated[0, len(ids)])], skip_special_tokens=True
        ).strip()
        if code not in {str(row["clean_sender_output"]), str(row["attacked_sender_output"])}:
            raise ValueError(f"invalid regenerated sender code for {case_id}: {code!r}")
        message = dict(row["clean_message"] if code == row["clean_sender_output"] else row["attacked_message"])
        if "message.whole" in mask:
            message = dict(row["clean_message"])
        elif "message.decision_code" in mask:
            clean_code = str(row["clean_sender_output"])
            message["decision_code"] = clean_code
            message["raw_sender_output"] = clean_code
        receiver_condition = "clean" if message["decision_code"] == row["clean_sender_output"] else "attacked"
        receiver_prompt, receiver_ids = _prompt_and_ids(row, "receiver", receiver_condition)
        receiver_inputs = _qualified_inputs(self.adapter, receiver_prompt, receiver_ids)
        self.adapter.intervention_application_counts = {}
        try:
            self._install_internal_patches(case_id, receiver_nodes, sender=False)
            logits = self.adapter.forward(receiver_inputs).logits[:, -1, :].detach().cpu()
            receiver_counts = dict(self.adapter.intervention_application_counts)
        finally:
            self.adapter.remove_hooks()
        expected = {node: 1 for node in (*sender_nodes, *receiver_nodes)}
        observed = {**sender_counts, **receiver_counts}
        if observed != expected:
            raise RuntimeError(f"intervention application counts differ: {observed} != {expected}")
        margin = float(logits[0, self.label_ids["A"]] - logits[0, self.label_ids["B"]])
        return {
            "case_id": case_id, "condition": condition, "margin_A_minus_B": margin,
            "sender_output": code, "message": message,
            "sender_input_token_ids": ids, "receiver_input_token_ids": receiver_ids,
            "intervention_application_counts": observed,
            "model_forward_steps": 5, "status": "ok",
        }

    def __call__(self, retained: tuple[str, ...]) -> Evaluation:
        """Return the frozen median metrics and every raw case execution."""
        mask = validate_mask(self.proposal, retained)
        attack_rows = [self._condition(row, mask, "attacked") for row in self.rows]
        clean_rows = [self._condition(row, mask, "clean") for row in self.rows]
        faithfulness: list[float] = []
        benign: list[float] = []
        for source, attacked, clean in zip(self.rows, attack_rows, clean_rows):
            baseline_clean = float(source["clean_receiver_raw_logit_a"] - source["clean_receiver_raw_logit_b"])
            baseline_attacked = float(source["attacked_receiver_raw_logit_a"] - source["attacked_receiver_raw_logit_b"])
            full = baseline_clean - baseline_attacked
            circuit = attacked["margin_A_minus_B"] - baseline_attacked
            faithfulness.append(1.0 - abs(full - circuit) / (abs(full) + 1e-6))
            benign.append(abs(clean["margin_A_minus_B"] - baseline_clean))
        return Evaluation(
            median(faithfulness), median(benign), 160,
            {"evidence_type": "real_model_intervention", "mask": list(mask),
             "attacked": attack_rows, "clean_identity": clean_rows,
             "faithfulness_per_case": faithfulness, "benign_damage_per_case": benign},
        )
