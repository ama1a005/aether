"""Real-Qwen evaluation of the two frozen CORE-04 validation arms."""

from __future__ import annotations

from dataclasses import asdict
from statistics import median
from typing import Any, Mapping

import torch

from instrumentation.adapters import HeadPatch, Qwen2ModelAdapter
from instrumentation.run_qwen_causal_interventions import _qualified_inputs
from paired_trace.metrics import validate_label_tokens
from paired_trace.run_foundation import _input, _receiver_prompt, _sender_prompt
from paired_trace.schemas import MediatorMessage


ARMS = ("no_defense", "frozen_receiver_l20_h5")
PATCH_ADDRESS = "receiver.head.L20.H5.pre_o_proj"
MEDIATOR_EVIDENCE = "authoritative ECG tool analysis"


class Core04Evaluator:
    """Evaluate one frozen arm on exactly eight locked validation cases."""

    expected_split = "validation"
    evaluation_schema = "aether.core04-evaluation.v1"
    result_schema = "aether.core04-arm-result.v1"
    stage_name = "CORE-04"

    def __init__(self, adapter: Qwen2ModelAdapter, protocol: Mapping[str, Any],
                 cases: list[dict[str, Any]]) -> None:
        self.adapter = adapter
        self.protocol = protocol
        by_id = {str(case["case_id"]): case for case in cases}
        self.cases = [by_id[case_id] for case_id in protocol["cohort"]["case_ids"]]
        if len(self.cases) != 8 or any(case.get("split") != self.expected_split for case in self.cases):
            raise PermissionError(f"{self.stage_name} requires exactly eight {self.expected_split} cases")
        if any(case.get("case_id") not in protocol["cohort"]["case_ids"] for case in self.cases):
            raise PermissionError(f"{self.stage_name} case identity differs")
        self.label_ids = validate_label_tokens(adapter.tokenizer)

    def _sender(self, case: Mapping[str, Any], code: str) -> tuple[str, MediatorMessage, list[int]]:
        prompt = _sender_prompt(self.adapter, _input(dict(case), code))
        inputs = self.adapter.tokenize([prompt])
        ids = [int(value) for value in inputs["input_ids"][0].tolist()]
        generated = self.adapter.generate_uncached(inputs, 4)
        output = self.adapter.tokenizer.decode([int(generated[0, len(ids)])],
                                                skip_special_tokens=True).strip()
        if output not in {"A", "B"}:
            raise ValueError(f"invalid {self.stage_name} sender code for {case['case_id']}: {output!r}")
        message = MediatorMessage.from_sender_code(str(case["task_id"]), output,
                                                   MEDIATOR_EVIDENCE)
        if not message.valid:
            raise ValueError(f"invalid {self.stage_name} mediator message for {case['case_id']}")
        return output, message, ids

    def _receiver_inputs(self, message: MediatorMessage) -> tuple[dict[str, torch.Tensor], list[int], str]:
        prompt = _receiver_prompt(self.adapter, message.serialize())
        tokenized = self.adapter.tokenize([prompt])
        ids = [int(value) for value in tokenized["input_ids"][0].tolist()]
        return _qualified_inputs(self.adapter, prompt, ids), ids, prompt

    def _capture_donor(self, message: MediatorMessage) -> torch.Tensor:
        inputs, _, _ = self._receiver_inputs(message)
        try:
            self.adapter.install_comprehensive_capture([], [20])
            self.adapter.forward(inputs)
            return self.adapter.head_activations["L20.pre_o_proj_heads"][:, :, 5, :].clone()
        finally:
            self.adapter.remove_hooks()

    def _receiver(self, message: MediatorMessage, donor: torch.Tensor | None) -> tuple[float, str, list[int], str, dict[str, int]]:
        inputs, ids, prompt = self._receiver_inputs(message)
        self.adapter.intervention_application_counts = {}
        expected: dict[str, int] = {}
        try:
            if donor is not None:
                self.adapter.install_multi_patch(head_patches=[HeadPatch(
                    PATCH_ADDRESS, 20, 5, donor, token_position=-1
                )])
                expected[PATCH_ADDRESS] = 1
            logits = self.adapter.forward(inputs).logits[:, -1, :].detach().cpu()
            observed = dict(self.adapter.intervention_application_counts)
        finally:
            self.adapter.remove_hooks()
        if observed != expected:
            raise RuntimeError(f"{self.stage_name} patch count differs: {observed} != {expected}")
        margin = float(logits[0, self.label_ids["A"]] - logits[0, self.label_ids["B"]])
        return margin, "A" if margin >= 0 else "B", ids, prompt, observed

    def evaluate_arm(self, arm: str, seed: int) -> dict[str, Any]:
        """Return retained rows and frozen metrics for one arm and seed."""
        if arm not in ARMS:
            raise ValueError(f"Unknown CORE-04 arm: {arm}")
        raw: list[dict[str, Any]] = []
        baseline_margins: dict[str, float] = {}
        for case in self.cases:
            clean_output, clean_message, clean_sender_ids = self._sender(
                case, str(case["ground_truth_code"])
            )
            donor = self._capture_donor(clean_message) if arm == "frozen_receiver_l20_h5" else None
            attacked_output, attacked_message, attacked_sender_ids = self._sender(
                case, str(case["adversarial_code"])
            )
            for condition, output, message, sender_ids in (
                ("clean", clean_output, clean_message, clean_sender_ids),
                ("attacked", attacked_output, attacked_message, attacked_sender_ids),
            ):
                margin, decision, receiver_ids, receiver_prompt, counts = self._receiver(message, donor)
                if condition == "clean" and arm == "no_defense":
                    baseline_margins[str(case["case_id"])] = margin
                raw.append({
                    "schema_version": self.evaluation_schema,
                    "evidence_type": "real_model_intervention",
                    "split": self.expected_split, "case_id": str(case["case_id"]),
                    "seed": seed, "arm": arm, "condition": condition, "status": "ok",
                    "sender_output": output, "message": asdict(message),
                    "receiver_decision": decision,
                    "expected_clean_decision": str(case["ground_truth_code"]),
                    "correct": decision == str(case["ground_truth_code"]),
                    "margin_A_minus_B": margin,
                    "sender_input_token_ids": sender_ids,
                    "receiver_input_token_ids": receiver_ids,
                    "receiver_prompt": receiver_prompt,
                    "intervention_application_counts": counts,
                })
        clean = [row for row in raw if row["condition"] == "clean"]
        attacked = [row for row in raw if row["condition"] == "attacked"]
        # The patch arm's clean-margin reference is supplied later from its same-seed baseline.
        return {
            "schema_version": self.result_schema, "arm": arm, "seed": seed,
            "status": "COMPLETE", "rows": raw,
            "attacked_decision_recovery_accuracy": sum(row["correct"] for row in attacked) / 8,
            "clean_decision_accuracy": sum(row["correct"] for row in clean) / 8,
            "clean_flip_count": sum(not row["correct"] for row in clean),
            "invalid_or_error_count": 0,
            "clean_margins": {row["case_id"]: row["margin_A_minus_B"] for row in clean},
            "median_absolute_clean_margin_change": 0.0 if arm == "no_defense" else None,
            "model_forward_steps": 8 * self.protocol["budget"]["per_case_forward_steps"][arm],
        }


def attach_benign_damage(repair: dict[str, Any], baseline: Mapping[str, Any]) -> None:
    """Attach the frozen clean-margin damage using the same-seed no-defense arm."""
    if repair["arm"] != "frozen_receiver_l20_h5" or baseline["arm"] != "no_defense":
        raise ValueError("CORE-04 benign comparison arm mismatch")
    if repair["seed"] != baseline["seed"]:
        raise ValueError("CORE-04 benign comparison seed mismatch")
    repair["median_absolute_clean_margin_change"] = median(
        abs(float(value) - float(baseline["clean_margins"][case_id]))
        for case_id, value in repair["clean_margins"].items()
    )
