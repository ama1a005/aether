# SmolLM2 second-model qualification freeze v1 — review package

## Decision requested

Review:
`configs/model_qualification/smollm2_1_7b_second_model_freeze_v1.json`

SHA-256:
`ced23b44a971e71e1c9bc216a447b0396c39e13fd6d4af6a20bdbab2d31271ed`

No SmolLM2 files have been downloaded and no qualification has executed. This
is a prospective model, task, threshold, instrumentation and failure-policy
freeze.

## Candidate recommendation

`HuggingFaceTB/SmolLM2-1.7B-Instruct` is proposed at immutable revision
`dfc017ec3d4e0eaed394f8bf2a0fd2ff24f8b2cd`.

Reasons:

- It is a genuinely distinct Llama-style decoder rather than another Qwen size.
- Its model card declares Apache-2.0 licensing.
- It is an instruction model with a documented Transformers chat template.
- Its 1.7B size fits the frozen CPU-float32 qualification condition.
- It uses a standard Transformers implementation without remote model code.
- The model card explicitly documents function-calling capability, though that
  does not guarantee it will pass AETHER's balanced task.

Primary source:
<https://huggingface.co/HuggingFaceTB/SmolLM2-1.7B-Instruct/blob/dfc017ec3d4e0eaed394f8bf2a0fd2ff24f8b2cd/README.md>

## Alternatives considered

- `microsoft/Phi-3-mini-4k-instruct`: MIT licensed and capable, but approximately
  3.8B parameters. Full float32 weights are about 15.2 GB before runtime
  overhead, which is a poor fit for a single 15 GB T4 and less safe under the
  frozen no-offload condition. Its historical model card also discusses custom
  code and special attention implementations.
- `google/gemma-2-2b-it`: capable and reasonably sized, but Hugging Face access
  requires separately accepting Google's usage license. This adds an avoidable
  gated-access dependency.
- `Qwen/Qwen2.5-0.5B-Instruct`: ineligible as a successful second-model claim
  because the retained balanced qualification already failed asymmetrically.

## Frozen qualification

The proposal reuses the unchanged balanced AETHER qualification cases, prompts,
labels and controls. It requires:

- 12/12 correct clean cases in each direction;
- 12/12 eligible attacked cases in each direction;
- 12/12 rescue and induction controls in each direction;
- zero invalid/error rows;
- passive-hook non-interference;
- activation round-trip persistence;
- exact hook cleanup;
- a nonzero fixed middle-layer intervention effect;
- CPU float32, seed 42, eager attention, no quantization or offload;
- no validation or test access.

Instrumentation layers are architecture-relative: layers 0, 12 and 23 for the
expected 24-layer model. Behavioral failure stops instrumentation. Any failure
is retained as valid negative evidence; thresholds and the candidate cannot be
changed within the attempt.

## Claim boundary

A complete PASS would establish portability to one distinct open-weight model.
It would not establish broad model-family generalization or a second causal
circuit. A separate prospective intervention study would still be required for
that stronger claim.

## Human checklist

- [ ] Candidate identity and immutable revision are acceptable.
- [ ] Apache-2.0 licensing is acceptable for the project.
- [ ] CPU float32/no-offload execution is acceptable.
- [ ] Reusing the unchanged primary balanced task is scientifically appropriate.
- [ ] Behavioral thresholds have not been weakened.
- [ ] Architecture-relative instrumentation sites are appropriate.
- [ ] Failure and negative-result handling are acceptable.
- [ ] Validation and test remain closed.
- [ ] The exact SHA-256 above was independently recomputed.

Approval must explicitly name this proposal and exact hash. Implementation and
model access remain forbidden until then.
