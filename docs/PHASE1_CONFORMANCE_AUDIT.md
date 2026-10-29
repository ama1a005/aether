# Phase 1 conformance audit — 2026-10-29

Phase 1 is incomplete. All Phase 1 requirements, including former optional
additions, are mandatory. Phase 2 remains separate. A passing software test
does not complete a real-model experiment. This audit supersedes earlier
completion language about the advanced intervention and PPO milestones.

## Follow-up repairs (2026-10-29)

- Red-team orchestration now has bounded recon, balanced four-family planning,
  fixed call accounting, clean/attack execution, deterministic debrief, durable
  raw attempts, structured events, safe resume and full manifests. Its executed
  rule-agent smoke is synthetic evidence; real MCP/Qwen campaigns remain pending.
  A separate official-SDK stdio backend completed the full 16-call campaign on
  demo fixtures without errors; external WSO2 and Qwen execution remain pending.
- PTB-XL structured metadata loading is implemented with explicit roots,
  diagnostic-superclass derivation and default fold-10 rejection. No official
  data was downloaded, so only constructed-fixture acceptance has run.
- Exact-version official BFCL and AgentDojo command runners are implemented.
  They retain official stdout/stderr and fail on missing/mismatched packages.
  Native evaluation is still pending installation, pinned versions and models.
- Matched multi-seed comparison now covers greedy, beam, region/size-matched
  random, PPO training search and independently evaluated frozen PPO policy.

- Checkpointed PPO inference is now implemented in discovery/rl/policy.py and
  included in synthetic acceptance manifests. It reports terminal choices
  independently of best-visited training masks. The executed smoke policy was
  infeasible (retained M); training search found M/R/S. Policy competence remains
  unproven. Multi-seed and real evaluator integrations remain mandatory.
- Removed fabricated missing-fixture fallback in target/case_loader.py; invalid
  sources/counts fail explicitly and synthetic loading uses a local RNG.
- Latest full suite: 306 passed, 5 skipped, including all 6 regression tests.

- PPO rewards now contain additive transition contributions and charge newly
  executed forward passes; cached evaluations incur no additional forward cost.
- Public intervention helpers reject invalid indices, non-finite activations,
  invalid head counts and codec shape/device mismatches. Hooks reject duplicate
  module targets and requested components that never execute.
- SAE feature patching preserves the original reconstruction residual. A lossy
  codec self-patch control verifies identity; trained SAE integration is pending.
- causal/interventions/path_replay.py adds three-stage mediator replay with
  explicit off-path baseline freezes. A branching toy test excludes a stronger
  bypass. This requires a caller-declared causal cut, evaluation mode and singly
  executed residual-output modules; general edge patching remains pending.
- Replaced all three assert-True discovery placeholders with meaningful tests.
- Regression subprocesses now run in a temporary workspace with copied fixture
  inputs. All six tests pass with no changes to tracked result artifacts.
- Verification after these repairs: 297 unit/integration passed, 5 skipped;
  6 regression passed. The remaining gaps below remain mandatory, including
  checkpointed policy evaluation, real evaluator wiring and native benchmarks.

The original findings below are retained as the audit record; the follow-up
list above identifies those resolved since that inspection.

Sources: Phase1Project.md sections 9–20, 81–82 and final deliverables;
4_ProjectDescription.md; RESEARCH_CONTRACT.md; TASK.md; docs/*PROTOCOL.md;
docs/RELIABILITY_CHECKPOINT.md; source and tests listed below. This is a
requirement-level review and targeted code inspection, not proof every line is
bug-free. Existing historical measurements remain unchanged.

| Mandatory requirement | Current evidence / implementation | Remaining acceptance |
|---|---|---|
| Python 3.11, dependency locks, CI | pyproject.toml, requirements locks, .github/workflows/ci.yml | Fresh environment install and remote CI result still need verification |
| Real MCP/A2A target | target/mcp, target/a2a; stdio SDK test; deterministic demo | WSO2 host transport previously failed; qualified live Qwen/FHIR campaign incomplete |
| Two-agent open model | instrumentation adapters, paired_trace; historical 0.5B runs | V2 behavioral competence failed; replacement model qualification required |
| Agent C | target/agents/agent_c.py, target/three_agent_pipeline.py; deterministic tests | Real-model/real-MCP wiring and attacked-case comparison; clean verification access must be explicit in threat model |
| Four attack families | attacks/corpus/builder.py build_phase1_corpus | Implicit family is generated text only; real execution, diversity, split freeze, eligibility and ASR missing |
| Red-team orchestration | attacks/orchestration.py; four-family rule-target acceptance | Real MCP/Qwen backend campaign and development split remain pending |
| PTB-XL provenance | benchmarks/ptbxl.py; fold-locked constructed-fixture tests | Download/hash v1.0.3, freeze task recipe and execute development folds |
| BFCL | Exact-version official command runner | Pin/install release, model handler/subset and execute official evaluator |
| MCPTox | benchmarks/mcptox.py; released-response smoke | Native/current-model comparison, licensing and official-compatibility limits unresolved |
| TAMAS | benchmarks/tamas.py; adapter smoke | Native benchmark execution and utility/security measurements missing |
| AgentDojo | Exact-version official command runner | Pin/install release, compatible model/suite/tasks and execute native utility/security evaluation |
| Tracr | calibration/tracr; historical compiler graph/output evidence | Actual intervention/known-circuit recovery requirement not discharged by compiler metadata alone |
| IOI/Greater-Than | calibration/ioi; historical GPT-2 calibration | Recheck pinned environment/model when available; preserve scope of historical calibration |
| Activation probes | evaluation/linear_probe.py; synthetic tests | Real activation comparison and official/released NARCBench reproduction missing |
| Receiver-only baseline | Greedy and receiver scope helpers | Same-context real evaluator, PPO receiver-only comparison and matched compute reporting missing |
| DCMG and BVP | causal graph and evidence modules; paired message rescue | No accepted full internal sender→mediator→receiver chain; specificity controls rejected historical candidates |
| Random/greedy/beam/PPO | Search, checkpoints, frozen inference and multi-seed comparison code | Execute multi-seed real intervention comparison; synthetic frozen policy currently failed |
| Reward ablations | Synthetic size/cost/stop ablations | Current constant-cost toy gives no informative cost ablation; benign/effect sensitivity and real data needed |
| Residual/head interventions | causal/interventions/advanced.py | Generic head operator assumes concatenated head tensors; hooking ordinary attention output after o_proj is invalid; use exact pre-projection adapter hooks |
| Path patching | execute_path_patch applies simultaneous node replacements | NOT edge/path isolation: requires staged reruns, freezing off-path activations and a discriminating control |
| SAE intervention | Codec interface and identity-codec test | Trained pinned SAE, reconstruction-error controls, feature provenance and adapter integration missing |
| Message field/span intervention | Existing structured mediator repair and bridge operations | Full span/field comparisons and negative controls under frozen data |
| Tri-location repairs | remediation/selector/frontier.py; tests | Real sender/message/receiver candidates, validation selection and untouched test evaluation |
| Statistics and negative controls | attacks/stats.py and causal-specificity foundations | Complete paired matrix, uncertainty, stability, invalid/error denominators, operator and scope ablations |
| Heterogeneous sender/receiver addition | Build requirement | Qualified second model and same-method comparison after instrumentation acceptance |
| Final deliverables | Manifests and partial result artifacts | Final tables/figures, external summary, frozen method, held-out evaluation, reproducible paper package |

## Confirmed defects corrected in this audit

- PPO rollout boundaries incorrectly used a zero bootstrap value even when the
  episode continued. Updates now bootstrap the next state's value; actual
  terminals still have zero future return. Tests check numerical targets.
- PPO gradient clipping now rejects non-finite gradient norms.
- Agent C accepted NaN/infinite/out-of-range verification scores. It now fails
  explicitly, including on boolean pseudo-numbers.
- The Phase 1 tier summary still described additions as conditional. They are
  now mandatory with dependency ordering.

## Further code issues requiring bounded fixes

- PPO returns the best visited mask, not a demonstrated learned policy; cache
  history is hidden from its observation and affects available actions. Treat
  the claimed MDP formulation as incomplete until its state/observation design
  and policy evaluation are specified and tested.
- Reward records contain absolute utility components but a delta total; they
  are not an additive decomposition of the transition reward. Constant forward
  cost cancels in utility differences. Resource-aware reward needs correction.
- Advanced public tensor helpers lack complete direct-call index/finite checks;
  generic hooks do not prove a requested component fired. SAE decoding currently
  changes reconstruction error as well as selected feature content.
- Legacy tests/unit/test_discovery.py contains three assert-True placeholders.
  Counts alone are therefore insufficient evidence of discovery correctness.
- Regression scripts rewrite tracked historical result files. Isolate their
  output before treating the suite as clean by construction.
- Root PROJECT_STATE.md and TASK.md contain historical DONE/in-progress claims;
  use dated current entries and this matrix for present status.

## Completion order

Verification on 2026-10-29: Python 3.11.9; unit/integration 284 passed, 5 skipped;
regression 6 passed; opt-in demo E2E 2 passed; frontend 4 passed and production
build passed; pip check passed. Frontend needed execution outside the filesystem
sandbox after esbuild configuration reads were denied. No real-model test ran.
Test-generated tracked artifacts were restored from HEAD after copying outputs
to .local/audit-20261029-generated. Existing frontend changes remain user-owned.

1. Fix the listed numerical/intervention validity issues and strengthen tests.
2. Complete real evaluator wiring, checkpointed RL comparisons and orchestration.
3. Complete data adapters/native benchmark runners and provenance manifests.
4. Qualify the exact replacement model on adequate hardware; see QWEN_EXECUTION_OPTIONS.md.
5. Execute development comparisons and controls; freeze method and selection.
6. Execute approved validation and once-only held-out tests; generate the paper
   tables directly from artifacts. Failed hypotheses remain valid findings.
