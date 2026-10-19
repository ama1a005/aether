"""Bounded CUDA load, forward, and repeated-generation acceptance."""
from __future__ import annotations
import json
from pathlib import Path
from time import perf_counter

import psutil
import torch

from demo.backend.model_runtime import _runtime, preload_model

def main() -> None:
    if not torch.cuda.is_available():
        raise SystemExit("CUDA unavailable")
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    before = torch.cuda.mem_get_info()
    host_before = psutil.virtual_memory().available
    started = perf_counter()
    status = preload_model()
    model, tokenizer = _runtime()
    load_seconds = perf_counter() - started
    if next(model.parameters()).device.type != "cuda" or next(model.parameters()).dtype != torch.float16:
        raise SystemExit("model parameters are not CUDA float16")
    prompt = "Reply with only the word READY."
    inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
    outputs = []
    with torch.inference_mode():
        _ = model(**inputs).logits
        for _index in range(2):
            generated = model.generate(**inputs, max_new_tokens=8, do_sample=False, pad_token_id=tokenizer.eos_token_id)
            outputs.append(tokenizer.decode(generated[0, inputs.input_ids.shape[1]:], skip_special_tokens=True))
    after = torch.cuda.mem_get_info()
    result = {"status": status, "load_seconds": load_seconds, "vram_free_before": before[0],
              "vram_free_after": after[0], "peak_vram_bytes": torch.cuda.max_memory_allocated(),
              "host_ram_available_before": host_before, "generated_token_count": sum(len(tokenizer.encode(x)) for x in outputs),
              "generations": outputs, "repeated_generation_pass": len(outputs) == 2}
    path = Path("demo/artifacts/live/model_acceptance.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
