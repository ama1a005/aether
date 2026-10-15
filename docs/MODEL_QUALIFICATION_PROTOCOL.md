# V2 Model Qualification Protocol

**Status:** BLOCKED BEFORE EXECUTION

**Parent checkpoint:** `d6725bee820c6374b1949a860df1ba0737b11304`

## Purpose

Model qualification was proposed because `Qwen/Qwen2.5-0.5B-Instruct` failed the balanced V2 behavioral prerequisite before any internal causal analysis. Its 24-case development result remains preserved: A clean 12/12, B clean 9/12, A-to-B attack success 8/12, and B-to-A attack success 12/12. Internal localization remains insufficient and untested under V2.

The sole proposed replacement is `Qwen/Qwen2.5-1.5B-Instruct`. It was selected in advance because it is a larger model in the same family, should require the smallest adapter change, has open weights, and is more plausible for local CPU execution than an approximately 3B fp32 model.

## Held constant

The V2.1 case registry, split assignments, semantic contents, class balance, attack mappings, control mappings, mediator schema, labels, score definition, prompts, templates, parser, generation settings, and development-only guard must remain unchanged. Validation and test remain closed. V1, V2.0, and V2.1 artifacts are immutable.

## Required pass rule

The replacement model may be evaluated only against the unchanged, predeclared V2 behavioral qualification gate. That gate must numerically specify, for each class/direction, the clean-competence requirement, directional attack-success requirement, eligibility requirement, and symmetry requirement.

The frozen V2 materials do not numerically specify those four pass thresholds. They define clean correctness as `S > 0`, attack success as attacked `S < 0`, and numerical thresholds for later causal-candidate classification, but describe the behavioral prerequisite only as requiring "reliable competence and attack behavior in both classes." The observed 0.5B result was declared insufficient, but that observation is not a reusable numerical decision rule.

Consequently, no pass/fail outcome can be assigned to a new model without inventing a post-hoc threshold. Task 2 of the model-qualification instruction explicitly requires stopping before running the model in this situation.

## Execution status

No 1.5B model metadata was resolved, no files were downloaded, no hardware feasibility run was performed, no tokenizer was loaded, and no development case was executed. No message intervention, activation capture, internal scan, or head search was run. No V2-MQ1 execution freeze or result manifest exists because an executable gate cannot yet be frozen honestly.

## Resolution required

A human-reviewed amendment must numerically predeclare all four behavioral criteria before any replacement-model output is observed. That amendment must be a new prospective qualification protocol; it must not rewrite V2.1 or reinterpret the 0.5B result. After approval, the 1.5B-only hardware, pinning, tokenizer-compatibility, development baseline, and conditional message-control sequence may begin.

On failure, stop and return to the Phase-1 pivot decision. On success, stop after message-level confirmation and prepare a separately reviewed model-specific instrumentation-acceptance stage.
