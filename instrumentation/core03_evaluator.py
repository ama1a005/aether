"""Real-Qwen evaluation of the five frozen CORE-03 repair arms."""

from __future__ import annotations

from statistics import median
from typing import Any, Mapping

import torch

from causal.qci_execution import parse_candidate
from instrumentation.adapters import HeadPatch, ModulePatch, Qwen2ModelAdapter
from instrumentation.run_qwen_causal_interventions import (
    _capture_sources,
    _module_site,
    _prompt_and_ids,
    _qualified_inputs,
)
from paired_trace.metrics import validate_label_tokens


RECEIVER_COMPONENTS = {
    "fixed_receiver_l22_attention": "module.L22.attention_output",
    "mechanism_receiver_l20_h5": "head.L20.H5.pre_o_proj",
}


class Core03Evaluator:
    """Evaluate one arm on the frozen four-case development-audit cohort."""

    def __init__(self, adapter: Qwen2ModelAdapter, protocol: Mapping[str, Any],
                 rows: list[dict[str, Any]]) -> None:
        self.adapter = adapter
        self.protocol = protocol
        indexed = {str(row["case_id"]): row for row in rows}
        self.rows = [indexed[case_id] for case_id in protocol["cohort"]["case_ids"]]
        if len(self.rows) != 4 or any(
            row.get("split") != "development" or not row.get("eligible") for row in self.rows
        ):
            raise PermissionError("CORE-03 requires four eligible development-audit cases")
        self.label_ids = validate_label_tokens(adapter.tokenizer)

    def _sender_message(self, row: dict[str, Any], condition: str) -> tuple[str, dict[str, Any], list[int]]:
        prompt, ids = _prompt_and_ids(row, "sender", condition)
        generated = self.adapter.generate_uncached(_qualified_inputs(self.adapter, prompt, ids), 4)
        code = self.adapter.tokenizer.decode(
            [int(generated[0, len(ids)])], skip_special_tokens=True
        ).strip()
        allowed = {str(row["clean_sender_output"]), str(row["attacked_sender_output"])}
        if code not in allowed:
            raise ValueError(f"invalid CORE-03 sender code for {row['case_id']}: {code!r}")
        message = dict(row["clean_message"] if code == row["clean_sender_output"] else row["attacked_message"])
        return code, message, ids

    def _receiver_inputs(self, row: dict[str, Any], message: Mapping[str, Any]) -> tuple[Any, list[int]]:
        condition = "clean" if message["decision_code"] == row["clean_sender_output"] else "attacked"
        prompt, ids = _prompt_and_ids(row, "receiver", condition)
        return _qualified_inputs(self.adapter, prompt, ids), ids

    def _install_receiver_patch(self, arm: str, source: torch.Tensor) -> str:
        identifier = RECEIVER_COMPONENTS[arm]
        candidate = parse_candidate({
            "agent": "receiver",
            "candidate_id": identifier,
            "family": "head" if identifier.startswith("head.") else "module",
        })
        address = f"receiver.{identifier}"
        if candidate.family == "head":
            self.adapter.install_multi_patch(head_patches=[HeadPatch(
                address, candidate.layer, int(candidate.head), source, token_position=-1
            )])
        else:
            self.adapter.install_multi_patch(module_patches=[ModulePatch(
                address, _module_site(self.adapter, candidate), source, token_position=-1
            )])
        return address

    def _capture_receiver_donor(self, row: dict[str, Any], arm: str) -> torch.Tensor:
        identifier = RECEIVER_COMPONENTS[arm]
        candidate = parse_candidate({
            "agent": "receiver", "candidate_id": identifier,
            "family": "head" if identifier.startswith("head.") else "module",
        })
        inputs, _ = self._receiver_inputs(row, row["clean_message"])
        return _capture_sources(self.adapter, inputs, [candidate])[identifier]

    def _receiver(self, row: dict[str, Any], message: Mapping[str, Any], arm: str,
                  donor: torch.Tensor | None) -> tuple[float, str, list[int], dict[str, int]]:
        inputs, ids = self._receiver_inputs(row, message)
        self.adapter.intervention_application_counts = {}
        expected: dict[str, int] = {}
        try:
            if donor is not None:
                address = self._install_receiver_patch(arm, donor)
                expected[address] = 1
            logits = self.adapter.forward(inputs).logits[:, -1, :].detach().cpu()
            observed = dict(self.adapter.intervention_application_counts)
        finally:
            self.adapter.remove_hooks()
        if observed != expected:
            raise RuntimeError(f"CORE-03 patch count differs: {observed} != {expected}")
        margin = float(logits[0, self.label_ids["A"]] - logits[0, self.label_ids["B"]])
        return margin, "A" if margin >= 0 else "B", ids, observed

    def evaluate_arm(self, arm: str, seed: int) -> dict[str, Any]:
        """Return all rows and frozen summary metrics for one arm and seed."""
        if arm not in {row["id"] for row in self.protocol["arms"]}:
            raise ValueError(f"Unknown CORE-03 arm: {arm}")
        raw: list[dict[str, Any]] = []
        for row in self.rows:
            donor = self._capture_receiver_donor(row, arm) if arm in RECEIVER_COMPONENTS else None
            for condition in ("clean", "attacked"):
                code, message, sender_ids = self._sender_message(row, condition)
                if arm == "fixed_message_whole":
                    message = dict(row["clean_message"])
                elif arm == "mechanism_message_decision_code":
                    clean_code = str(row["clean_sender_output"])
                    message["decision_code"] = clean_code
                    message["raw_sender_output"] = clean_code
                margin, decision, receiver_ids, counts = self._receiver(row, message, arm, donor)
                expected = str(row["clean_sender_output"])
                raw.append({
                    "schema_version": "aether.core03-evaluation.v1",
                    "evidence_type": "real_model_intervention",
                    "split": "development_audit",
                    "case_id": str(row["case_id"]), "seed": seed, "arm": arm,
                    "condition": condition, "status": "ok", "sender_output": code,
                    "message": message, "receiver_decision": decision,
                    "expected_clean_decision": expected, "correct": decision == expected,
                    "margin_A_minus_B": margin,
                    "sender_input_token_ids": sender_ids,
                    "receiver_input_token_ids": receiver_ids,
                    "intervention_application_counts": counts,
                })
        clean = [row for row in raw if row["condition"] == "clean"]
        attacked = [row for row in raw if row["condition"] == "attacked"]
        baseline = {str(row["case_id"]): float(
            row["clean_receiver_raw_logit_a"] - row["clean_receiver_raw_logit_b"]
        ) for row in self.rows}
        forward_steps = sum(self.protocol["budget"]["per_case_forward_steps"][arm] for _ in self.rows)
        return {
            "schema_version": "aether.core03-arm-result.v1", "arm": arm, "seed": seed,
            "status": "COMPLETE", "rows": raw,
            "attacked_decision_recovery_accuracy": sum(row["correct"] for row in attacked) / 4,
            "clean_decision_accuracy": sum(row["correct"] for row in clean) / 4,
            "clean_flip_count": sum(not row["correct"] for row in clean),
            "invalid_or_error_count": 0,
            "median_absolute_clean_margin_change": median(
                abs(row["margin_A_minus_B"] - baseline[row["case_id"]]) for row in clean
            ),
            "model_forward_steps": forward_steps,
        }
