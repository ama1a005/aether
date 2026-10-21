# Experiment Ledger

## REVIEW-RELIABILITY-20261021 (engineering verification, not a scientific experiment)

Executed all 48 mock HTTP actions over DEMO-PAT-001..012; verified clean correctness
and rescue recovery. Real stdio MCP integration passed with the installed SDK.
External WSO2 host initialization failed on HTTP framing, including after a
stateless-container restart; in-container initialization returned valid JSON.
No external all-12 pipeline qualification or Qwen experiment is claimed. Test and
smoke results are summarized in `RELIABILITY_CHECKPOINT.md`; historical research
artifacts are preserved, not replaced by test-generated timestamp updates.

## DEMO-LIVE-QWEN05-MCP-12 — NOT RUN (2026-10-19)

- Scope: 12 fixed synthetic cases, clean/attack and qualifying rescue.
- Model: `Qwen/Qwen2.5-0.5B-Instruct@7ae557604adf67be50417f59c2c2f167def9a775`.
- MCP: `aether-clinical-tools` stdio with official Python SDK `mcp==2.3.0`.
- Blocker: trust-store mode fixed initial TLS verification, but the local proxy repeatedly corrupted package responses before installation.
- No qualification numbers or live artifacts were produced.
- Intended command: `.\.venv-demo-gpu\Scripts\python.exe scripts\qualify_demo_live.py`.

| Date | Run | Result | Evidence | Scope |
|---|---|---|---|---|
| 2026-10-11 | Baseline suite | 83 passed, 0 failed, 0 skipped; 1 warning | terminal output | Before Stage-0 changes |
| 2026-10-11 | P1 target smoke | PASS; clean pass 87.5%, mock attack success 100% | `results/raw/p1_review_target_results.csv` | Rule-based/synthetic |
| 2026-10-11 | P2 attack smoke | PASS; 15 mock attacks | `results/raw/p2_review_attack_results.csv` | Not official MCPTox |
| 2026-10-11 | P3 smoke | PASS; 4/4 verification checks | `results/raw/p3_smoke_circuit_result.json` | ToyTransformer |
| 2026-10-11 | P4 smoke | PASS; 7/7 verification checks | `results/raw/p4_smoke_circuit_result.json` | Synthetic benchmark |
| 2026-10-11 | End-to-end smoke | PASS; 9/9 checks | `results/raw/e2e_smoke_summary.json` | Mock/synthetic |
| 2026-10-11 | Post-change suite | 84 passed, 0 failed, 0 skipped; 1 warning | terminal output | Includes manifest test |
| 2026-10-11 | Stage-0 manifest | PASS | `results/manifests/P0_stage0_20261011_verified_baseline_0.json` | Actual environment/artifact metadata |
| 2026-10-11 | Manifest-hardening suite | 85 passed, 0 failed, 0 skipped; 1 warning | terminal output | Adds required dataset identity, split/subset, timing and artifact hashes |
| 2026-10-12 | Stage-0 checkpoint verification | 85 passed; five smoke commands passed | commit `1b52b565e346e520cc474ac61eeca5a09c5896ac` | No models present at checkpoint |
| 2026-10-12 | Real-model instrumentation smoke | PASS; `Safe`; passive max logit delta `0.0`; L12 MLP zero-ablation delta `13.126136779785156` and output `safe` | `results/manifests/P0_mech_20261012_real_instrumentation_0.json`; activation SHA-256 `9c60bb97dcbd3c3e806ea3df89e2db525c600d746e8eec5a8cf26bd4bafb98ab` | Pinned Qwen2.5-0.5B, fp32 CPU; pipeline verification only |
| 2026-10-12 | Real-enabled full suite | 88 passed, 0 failed, 0 skipped; 1 warning | terminal output | Includes real hook non-interference test |
| 2026-10-13 | Real-model instrumentation checkpoint | PASS | commit `1a7f3ad` | No model weights or activation tensors committed |
| 2026-10-13 | Tracr reverse calibration | 3/3 exact outputs; 8-node/9-edge compiler graph recorded | `results/calibration/tracr/manifest.json` | Known-structure calibration only; no JAX intervention |
| 2026-10-13 | GPT-2 Small IOI calibration | 24/24 baseline; passive delta `0.0`; known recovery `0.3880`; random mean `0.0026`; gate PASS | `results/calibration/ioi/manifest.json` | Published name-mover subset; calibration, not discovery |
| 2026-10-13 | Calibration-enabled full suite | 96 passed, 0 failed, 0 skipped; 1 warning | terminal output | Both pinned real-model integration tests enabled |
| 2026-10-14 | Mechanistic calibration checkpoint | PASS | commit `28ecd11` | Approved calibration state before paired AETHER traces |
| 2026-10-14 | Paired real AETHER development traces | 16/16 clean-correct and attack-success; 0 invalid/excluded; attack effect `-4.485543727874756` | `results/phase1/paired_real/manifest.json` | Pinned Qwen2.5-0.5B, synthetic ECG substrate; development split only |
| 2026-10-14 | BVP foundation | Level 1 accepted; Levels 2 and 3 rejected; full path not verified | `results/phase1/paired_real/summary.json` | Whole-message recovery `1.0`; internal patches are exploratory null/negative results |
| 2026-10-14 | Paired-foundation full suite | 109 passed, 0 failed, 0 skipped; 1 known cache warning | terminal output | Real-model and calibration integration gates enabled |
| 2026-10-14 | Smoke verification | P1, P2, P3, P4, end-to-end, aggregate 3/3, and real instrumentation all passed | terminal output | Historical generated artifacts restored after verification |
| 2026-10-14 | BVP foundation checkpoint | PASS | commit `b531b7d` | Approved paired real traces and BVP foundation |
| 2026-10-14 | MCPTox released-response smoke | 20 records: 2 success, 14 ignored, 4 direct execution; released Qwen3-8B ASR `0.10` | `results/phase1/mcptox/smoke/manifest.json` | Official-compatible released-response rescoring; not local Qwen-0.5B inference |
| 2026-10-14 | TAMAS adapter smoke | 300/300 records loaded; 10 serialized | `results/phase1/tamas/smoke/manifest.json` | Adapter-only; no native framework/model evaluation |
| 2026-10-14 | Coarse internal causal scan | 18 sites/role; 4 sender and 10 receiver candidates supported under DEV rule | `results/phase1/causal_discovery/manifest.json` | Positive-control substrate, development only; 78 model queries, 563.16 s |
| 2026-10-14 | Standardized-anchor/discovery full suite | 121 passed, 0 failed, 0 skipped; 1 known cache warning | terminal output | Real-model and calibration integration gates enabled; validation/test untouched |
| 2026-10-14 | Standardized-anchor/discovery checkpoint | PASS | commit `34848c1` | Approved development evidence before specificity hardening |
| 2026-10-14 | Causal-specificity hardening | 0/6 candidates survived; all failed shuffled-source separation | `results/phase1/causal_specificity/manifest.json` | 16 development pairs only; 67 queries; 698.42 s; validation/test unopened |
| 2026-10-14 | Sender bidirectional refinement | L14 block rescue/induction `1.0/0.0`; L14 attention `1.0/0.0`; L18 block `1.0/1.0`; shuffled rescue `1.0` for all | `results/phase1/causal_specificity/hardening_results.json` | Coarse effects not case-specific |
| 2026-10-14 | Receiver bidirectional refinement | L23 block `1.0/1.0`; L18 block `0.4591/0.6814`; L14 attention `0.0533/0.1740`; shuffled effects comparable | `results/phase1/causal_specificity/hardening_results.json` | Fixed serialized messages; no supported internal candidate |
| 2026-10-14 | Method-freeze assessment | DO NOT FREEZE METHOD | `docs/PHASE1_METHOD_FREEZE_CANDIDATE.md` | Redesign on development before validation |
| 2026-10-15 | Hardening-complete gated suite | 126 passed, 0 failed, 0 skipped; 1 known cache warning | terminal output | Real-model and calibration gates enabled |
| 2026-10-15 | Hardening-complete smoke verification | P1, P2, P3, P4, end-to-end, aggregate 3/3, real instrumentation, MCPTox summary-only, TAMAS adapter: all PASS | terminal output | Historical generated artifacts restored; no API spending |
| 2026-10-15 | Causal-specificity hardening checkpoint | PASS | commit `303e0d8` | V1 preserved; coarse internal localization rejected under V1 controls |
| 2026-10-15 | Qwen generation/head acceptance | PASS; cached/uncached greedy identical, passive logits/output unchanged, head concat exact | `tests/integration/test_hook_non_interference.py` | 2 tests passed; CPU runtime 1750.86 s |
| 2026-10-15 | Balanced V2.0 behavior smoke | Gate FAIL; invalid/right-padding behavior identified | `results/phase1/balanced_v2/smoke/manifest.json` | Preserved diagnostic; no causal effects run |
| 2026-10-15 | Balanced V2.1 behavior smoke | A→B clean 4/4, attack 2/4; B→A clean 2/4, attack 4/4; invalid 0 | `results/phase1/balanced_v2/smoke_v2_1/manifest.json` | Behavioral gate still failed |
| 2026-10-15 | Balanced V2.1 full development baseline | A→B clean 12/12, attack 8/12; B→A clean 9/12, attack 12/12 | `results/phase1/balanced_v2/full_v2_1/manifest.json` | Message rescue/induction/field repair 1.0 on 8 and 9 eligible cases; internal search stopped |
| 2026-10-15 | V2 redesign decision | PIVOT PHASE 1 recommended | `docs/PHASE1_PIVOT_DECISION.md` | Human review required; validation/test unopened |
| 2026-10-15 | V2-complete test suite | 135 passed, 0 failed, 2 expected real-model skips; 1 known cache warning | terminal output | Calibration gate enabled; opt-in Qwen tests separately passed 2/2 |
| 2026-10-15 | Balanced V2 behavioral-gate checkpoint | PASS | commit `d6725be` | V1 restored unchanged; V2.0/V2.1 and closed validation/test preserved |
| 2026-10-15 | Qwen2.5-1.5B model qualification preflight | BLOCKED before execution | `docs/MODEL_QUALIFICATION_PROTOCOL.md` | Frozen behavioral gate lacks numerical aggregate pass thresholds; no download, model run, or intervention |
| 2026-10-16 | MQ-G1 prospective freeze | FROZEN before 1.5B access | protocol `64badcea20c43ba7a42f3b8134aa261805484d4bff38841a7130584108827c89`; config `d1c06af5a30ec6194bf974bc3ce8b7507cb4fe777f695d83a79b06830135c42b` | Development-stage rule; not retroactive to 0.5B |
| 2026-10-16 | Qwen2.5-1.5B hardware preflight | BLOCKED_NOT_EXECUTED | `results/phase1/model_qualification/v2_mq1/manifest.json` | 15.67 GiB installed, 1.66 GiB available; no model access/download, inference, intervention, validation, or test |
| 2026-10-16 | MQ-HW1 prospective freeze | FROZEN before retry measurement | protocol `18bd44883692e013e735b4b0ae6fcc7599d0c69f59b195de2de7c0aa53d0ca4d`; config `68d2d2d32e3687aa82350f0944073abdcc5c91c5f7480699c51ee59adfbf0d69` | Parent MQ protocol/config unchanged; no model access |
| 2026-10-16 | MQ-HW1 retry measurement | BLOCKED_PRE_ACCESS | `results/phase1/model_qualification/v2_mq_hw1_retry/hardware_measurement.json` | 15.67 GiB installed; 1.487 GiB available; 13.255 GiB disk free; no model access |
| 2026-10-16 | MQ-HW1 evaluator unit suite | 139 passed, 0 failed | `tests/unit/test_model_qualification.py` | Includes thresholds, disk, post-load state, one-model/fp32/no-quantization and split locks; no model download |
| 2026-10-19 | MQ-HW1 pre-model recheck after manual cleanup | BLOCKED_PRE_ACCESS | `results/phase1/model_qualification/v2_mq_hw1_retry/hardware_recheck_20261019.json` | 15.67 GiB installed; 2.814 GiB available; 24.392 GiB disk free; no model/tokenizer access |

Numeric smoke outputs are generated by existing mock/toy programs and are not paper evidence.
# Review demo engineering verification — 2026-10-19

This is a software/demo verification entry, not a new research experiment. Twelve synthetic cases were executed through the deterministic clean, one-field attack, and whole-message rescue paths to produce labelled replay bundles under `demo/artifacts/replays/`. The path records zero validation and zero test executions and states `model.used_for_this_run=false`. These artifacts demonstrate review behavior only and must not be pooled with model experimental results.
