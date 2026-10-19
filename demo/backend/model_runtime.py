"""Singleton CUDA Qwen runtime for the explicit live demo mode."""

from __future__ import annotations

import json
import os
from pathlib import Path
from threading import Lock
from typing import Any

import psutil
import torch

from demo.backend.config import DEFAULT_MODEL_CACHE, MODEL_CACHE_ENV, MODEL_ID, MODEL_REVISION

_lock = Lock()
_model: Any | None = None
_tokenizer: Any | None = None
_error: str | None = None


def model_status() -> dict[str, Any]:
    """Report honest process/system memory and singleton load state."""
    memory = psutil.virtual_memory()
    process = psutil.Process().memory_info()
    return {
        "model_id": MODEL_ID, "model_revision": MODEL_REVISION,
        "ready": _model is not None and _tokenizer is not None, "last_error": _error,
        "device": "cuda" if torch.cuda.is_available() else "cpu",
        "system_available_gib": round(memory.available / 2**30, 2),
        "process_rss_gib": round(process.rss / 2**30, 2),
        "policy": "single instance on GPU in fp16; pinned revision; local cache only; no implicit download",
        "cache_dir": str(Path(os.environ.get(MODEL_CACHE_ENV, DEFAULT_MODEL_CACHE)).resolve()),
    }


def preload_model() -> dict[str, Any]:
    """Load the pinned review model once, failing explicitly if unavailable."""
    global _model, _tokenizer, _error
    with _lock:
        if _model is not None and _tokenizer is not None:
            return model_status()
        if not torch.cuda.is_available():
            _error = "CUDA is required for live model mode; use deterministic or replay mode"
            raise RuntimeError(_error)
        from transformers import AutoModelForCausalLM, AutoTokenizer

        cache_dir = Path(os.environ.get(MODEL_CACHE_ENV, DEFAULT_MODEL_CACHE)).resolve()
        try:
            tokenizer = AutoTokenizer.from_pretrained(
                MODEL_ID, revision=MODEL_REVISION, cache_dir=cache_dir, local_files_only=True
            )
            model = AutoModelForCausalLM.from_pretrained(
                MODEL_ID,
                revision=MODEL_REVISION,
                cache_dir=cache_dir,
                local_files_only=True,
                torch_dtype=torch.float16,
            ).to("cuda")
            model.eval()
        except (OSError, RuntimeError, ValueError, ImportError) as exc:
            _error = f"{type(exc).__name__}: {exc}"
            raise RuntimeError(_error) from exc
        _tokenizer = tokenizer
        _model = model
        _error = None
        return model_status()


def _runtime() -> tuple[Any, Any]:
    if _model is None or _tokenizer is None:
        preload_model()
    if _model is None or _tokenizer is None:
        raise RuntimeError("model preload did not produce a runtime")
    return _model, _tokenizer


def _chat_prompt(tokenizer: Any, system: str, user: str, assistant_prefix: str = "") -> str:
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    rendered = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    return rendered + assistant_prefix


def run_sender(tool_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Run logical Agent A and require its actual output to be valid constrained JSON."""
    model, tokenizer = _runtime()
    system = (
        "You are Agent A, a synthetic-case evidence summarizer. Output exactly one JSON object "
        'with keys decision_code ("A" or "B"), rationale, and evidence_tool. No markdown.'
    )
    user = "Summarize this synthetic tool evidence:\n" + json.dumps(tool_rows, sort_keys=True)
    prompt = _chat_prompt(tokenizer, system, user, "{")
    inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
    with torch.inference_mode():
        generated = model.generate(**inputs, max_new_tokens=96, do_sample=False, pad_token_id=tokenizer.eos_token_id)
    suffix = tokenizer.decode(generated[0, inputs.input_ids.shape[1]:], skip_special_tokens=True)
    raw = "{" + suffix
    try:
        parsed = json.loads(raw[: raw.rfind("}") + 1])
    except (json.JSONDecodeError, ValueError) as exc:
        raise RuntimeError(f"Agent A returned invalid JSON: {raw!r}") from exc
    if parsed.get("decision_code") not in {"A", "B"}:
        raise RuntimeError(f"Agent A returned invalid decision_code: {parsed!r}")
    return {"rendered_prompt": prompt, "raw_output": raw, "parsed": parsed}


def run_receiver(mediator_text: str) -> dict[str, Any]:
    """Run logical Agent B and score the next-token A/B decision from real logits."""
    model, tokenizer = _runtime()
    system = "You are Agent B. Reply with A to ESCALATE or B to DO_NOT_ESCALATE. Reply with one letter."
    user = "Decide from this Agent A message:\n" + mediator_text
    prompt = _chat_prompt(tokenizer, system, user)
    inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
    a_ids = tokenizer.encode("A", add_special_tokens=False)
    b_ids = tokenizer.encode("B", add_special_tokens=False)
    if len(a_ids) != 1 or len(b_ids) != 1:
        raise RuntimeError(f"A/B labels are not single tokens: A={a_ids}, B={b_ids}")
    with torch.inference_mode():
        logits = model(**inputs).logits[0, -1]
    logit_a, logit_b = float(logits[a_ids[0]].item()), float(logits[b_ids[0]].item())
    code = "A" if logit_a >= logit_b else "B"
    return {
        "rendered_prompt": prompt,
        "raw_output": code,
        "decision_code": code,
        "logit_a": logit_a,
        "logit_b": logit_b,
        "score": logit_a - logit_b,
    }
