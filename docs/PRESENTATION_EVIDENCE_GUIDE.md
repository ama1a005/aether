# AETHER Phase-1 presentation and evidence guide

**Current as of:** 21 November 2026
**Integrated causal baseline:** `lm` at commit `516cfb1`
**PTB-XL demo implementation source:** commit `3f6592f`
**Purpose:** give an accurate, formal account of the work completed without
converting a project-authored fixture, compatibility smoke, or failed gate into
an official benchmark result.

## One-minute presentation statement

> AETHER is a mechanistic auditing framework for multi-agent AI systems. It
> traces an adversarial influence from a sender model, through a serialized
> inter-agent message, into a receiver model's decision. We implemented the
> complete real-Qwen experimental pipeline: immutable model qualification,
> passive-safe activation hooks, paired clean and attacked traces, heterogeneous
> sender/message/receiver interventions, five matched search methods,
> mechanism-guided remediation, locked validation and a once-only test. On the
> frozen balanced AETHER task, the explicit message decision code was the
> strongest one-node mediator, while receiver head L20H5 was the selected
> internal repair point. The paired-clean-donor L20H5 intervention recovered all
> attacked decisions in the eight-case locked validation and eight-case
> once-only test cohorts while preserving all clean decisions. Both held-out
> comparisons had exact paired McNemar p=0.0078125. The repair is an
> oracle-dependent causal probe on a synthetic research substrate, not a
> deployable clinical defense. Supporting SAE, second-model and Agent-C studies
> were completed and retained even when they did not meet their frozen positive
> criteria.

## What is official, reproduced, project-created, or merely prepared

Use these words consistently:

- **Official-source data:** bytes obtained from a named upstream release and
  checked against a pinned version or hash.
- **Official evaluator:** upstream evaluation code was actually executed.
- **Official-compatible:** upstream records/labels or evaluator semantics were
  preserved, but the execution is not an unmodified leaderboard configuration.
- **Reproduction/calibration:** a published task or program was recreated under
  a pinned model/repository for instrumentation validation.
- **AETHER project artifact:** cases, attacks, labels or task transformations
  constructed specifically for this project.
- **Official-source derived demo:** presentation-only records extracted from a
  named, hash-pinned public dataset with a disclosed AETHER label mapping;
  never described as an official benchmark result or pooled into causal-task
  statistics.
- **Prepared integration:** code exists, but no accepted experimental result
  exists.

## Demonstrable completed work

### Real-model experimental chain

1. Qwen2.5-1.5B-Instruct was pinned to immutable revision
   `989aa7980e4cf806f80c7fef2b1adb7bc71aa306` and passed the frozen behavioral
   qualification.
2. Passive hooks were tested for non-interference before broad capture.
3. Sender and receiver module/head activations were retained for paired clean
   and attacked executions.
4. QCI-1 produced a valid negative case-specific result; no threshold was
   relaxed.
5. QCI-2 identified and independently replicated four decision-semantic
   candidates on untouched development-audit cases.
6. Greedy, beam, matched random, flat PPO and receiver-only searches were
   compared under frozen budgets and independent caches.
7. The distributed-capable methods selected `message.decision_code`; the
   receiver-only method selected `receiver.head.L20.H5.pre_o_proj`.
8. A remediation study selected the L20H5 paired-clean-donor intervention.
9. That exact intervention passed locked validation and the once-only test.

### Held-out result

| Cohort | Unique cases | No-defense attacked accuracy | L20H5 attacked recovery | Clean accuracy | Exact McNemar p |
|---|---:|---:|---:|---:|---:|
| Development audit | 4 | 0.0 | 1.0 | 1.0 | 0.125 |
| Locked validation | 8 | 0.0 | 1.0 | 1.0 | 0.0078125 |
| Once-only test | 8 | 0.0 | 1.0 | 1.0 | 0.0078125 |

The three deterministic seeds are repeatability checks, not three independent
copies of each case. The Wilson 95% recovery interval for each eight-case held-
out cohort is approximately `[0.676, 1.000]`.

### Supporting experiments

- **SAE:** three seeds completed 100 epochs each. No checkpoint met both frozen
  reconstruction and sparsity rules, so the SAE was rejected and no feature-
  level claim was made.
- **SmolLM2:** the second model obtained 12/12 clean class-A decisions and 0/12
  class-B decisions. It failed balanced qualification and instrumentation
  stopped as required.
- **Agent C:** 48/48 rows were valid. Incoming accuracy was 0.5; reviewed
  accuracy was 0.4375; paired difference was -0.0625 with exact McNemar
  p=0.7011. Execution integrity passed, but improvement was not demonstrated.
- **Red team:** the retained attempt contained 48 inference errors and is
  rejected by the hardened verifier. No robustness score is claimed.

## How to present the demo

1. State that the active `DEMO-PAT-*` cohort is derived from twelve exact
   PTB-XL v1.0.3 records in folds 1–8, under CC BY 4.0. Show the source record
   ID and provenance panel.
2. Show a clean deterministic execution and its serialized mediator message.
3. Show the one-field attacked execution and changed decision.
4. Show clean-message rescue/attacked-message induction as causal illustrations.
5. Open the evidence page and distinguish live demo execution from retained
   real-Qwen experiments.
6. Present CORE-02 through CORE-05 as the scientific chain.

The local HAPI FHIR representation and WSO2 MCP connection are genuine software
and protocol operations over PTB-XL-derived metadata. This demonstrates
integration; it is not clinical validation, a native PTB-XL task, or evidence
that AETHER used unreported symptoms, labs or bedside measurements.

## Defensible novelty statement

The primary contribution is the heterogeneous cross-agent causal formalism and
workflow: sender internals, message fields, receiver internals and outcome nodes
share one intervention/search graph. RL, MCP, tool poisoning, activation
patching and multi-agent systems individually are prior art. The additional
contribution is mechanism-guided intervention selection under frozen
development, validation and once-only test discipline.

## Required limitations statement

The retained result does not establish an oracle-free defense, clinical or
population validity, global circuit minimality, a complete distributed internal
pathway, positive second-model generalization, official BFCL/MCPTox/TAMAS
performance, or deployment readiness. These are evidence boundaries, not hidden
implementation failures.

## Short answers for reviewers

**Did the project use real models?** Yes. The central causal chain used the
pinned Qwen2.5-1.5B-Instruct snapshot and real internal activations.

**Are the demo cases official-source records?** Yes. The active cases are
derived from twelve exact PTB-XL v1.0.3 development-fold records. The displayed
binary action is AETHER-derived and must not be called an official PTB-XL label.
PTB-XL is de-identified public research data; AETHER does not expose names or
raw waveforms in the demo.

**Why is the demo action derived?** PTB-XL provides ECG diagnostic statements,
not an escalation decision. The disclosed NORM/non-NORM mapping makes the
security demonstration deterministic without inventing unavailable clinical
fields. It supports a software demonstration, not clinical validity.

**Did RL win?** No superiority claim is supported. Flat PPO reached the same
terminal message bottleneck as simpler methods and was more expensive. The
novel element is the cross-boundary MDP/search representation, not generic PPO.

**Was every experiment positive?** No. The project retained negative SAE,
second-model and Agent-C outcomes under rules frozen before observation. That is
part of the experimental contribution and prevents post-hoc threshold changes.

**Is the repair deployable?** Not yet. It uses the matched clean activation as
an oracle donor. It is evidence of causal localization and repair potential.

