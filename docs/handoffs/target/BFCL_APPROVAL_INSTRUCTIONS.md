# BFCL protocol approval checklist

The BFCL runner requires a human approval decision bound to the exact bytes of
`configs/benchmarks/phase1_external.yaml`. No approval JSON is included in this
repository. Do not create or commit the template below until an authorized human
has reviewed and approved the protocol.

## Review these items

1. The assignment and `docs/benchmarks_nov19/BFCL_RUNBOOK.md`, including the
   disclosed-adapter claim boundary. This is BFCL's official evaluator with the
   AETHER Qwen adapter; it is not an unmodified leaderboard-model submission.
2. The frozen config SHA-256 below and its four prespecified Phase-1 categories:
   `simple`, `multiple`, `parallel`, `irrelevance`. This is a complete evaluation
   of those four categories only, not the full BFCL category suite and not a
   leaderboard result. Do not edit the config to make a runtime pass.
3. Target model `Qwen/Qwen2.5-1.5B-Instruct`, model and tokenizer revision
   `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`, and pinned wheel SHA-256.
4. The use of BFCL's native generation and evaluation commands, with invalid and
   error attempts included in denominators.
5. Split terminology: BFCL's own official evaluation/test cases may be
   evaluated. `split: development` means the AETHER project development scope;
   no AETHER validation or test split may be accessed.
6. Required Linux CUDA inference hardware and the no-model-access preflight.
7. The pinned runtime compatibility set: Python 3.11.9, `uv==0.11.8`,
   `vllm==0.34.0`, `torch==2.14.0`, CUDA 13.0, NVIDIA driver R580 or newer,
   and a GPU with at least 16 decimal GB memory and compute capability 7.5+.
   The project's general lock pins Torch 2.14.1; the isolated external BFCL
   overlay intentionally selects Torch 2.14.0 to match the vLLM CUDA wheel.

Frozen config SHA-256: `017bce07725a36ed4f7d8f08b399a22c1b4092271c2ce2473b2fd138b5e4ff75`.
If it differs locally, stop and obtain a new human review; do not silently
recompute the approval hash.

## Human decision file

Only after approval, the human reviewer creates
`results/phase1/protocol_approvals/bfcl_official.json` with this schema and
their real name:

```json
{
  "schema_version": "aether.protocol-decision.v1",
  "approved": true,
  "reviewer": "<reviewing human's full name>",
  "proposal_sha256": "017bce07725a36ed4f7d8f08b399a22c1b4092271c2ce2473b2fd138b5e4ff75",
  "validation_authorized": false,
  "test_authorized": false
}
```

Commit only this reviewed approval artifact, then repin the BFCL notebook to the
new source commit and commit that notebook update. The external run must use that
commit. Never authorize validation/test through this supporting benchmark gate.
