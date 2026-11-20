# Phase-1 local closure status — 20 November 2026

## Decision

All work that can be completed locally without executing the deferred official
benchmarks or retrying retained model experiments is implemented and verified.
The scientific state remains **INCOMPLETE**, because a completed negative result
does not satisfy a completion gate that prospectively required a positive
result. This report does not weaken or remove any frozen gate.

## Verified central result

AETHER's causal core is complete on the frozen Qwen2.5-1.5B-Instruct balanced
synthetic task. The selected paired-clean-donor intervention at receiver head
`L20H5` recovered attacked decisions while preserving clean decisions:

| Cohort | Unique cases | Baseline attacked accuracy | Repaired attacked accuracy | Clean accuracy | Exact paired McNemar p |
|---|---:|---:|---:|---:|---:|
| Development audit | 4 | 0.0 | 1.0 | 1.0 | 0.125 |
| Locked validation | 8 | 0.0 | 1.0 | 1.0 | 0.0078125 |
| Once-only test | 8 | 0.0 | 1.0 | 1.0 | 0.0078125 |

Seeds 11, 22 and 33 are deterministic repetitions and are not counted as
independent cases. The repair requires a matched clean activation donor and is
not an oracle-free deployable defense. The authoritative generated report is
`results/phase1/causal_core_report/CAUSAL_CORE_REPORT.md`.

## Newly retained supporting evidence

### Qwen sparse autoencoder

The retained v1.3 archive independently verifies. Seeds 11, 22 and 33 each
completed 100 epochs. No seed produced a checkpoint satisfying the frozen
reconstruction and sparsity eligibility criteria. The terminal scientific
outcome is `SAE_REJECTED_NO_ELIGIBLE_SEED`. No feature-level causal claim is
authorized. Large activation arrays and PyTorch checkpoints remain ignored and
outside Git; the compact summaries, histories, hashes and ingestion receipt are
retained under `results/phase1/sae/qwen15b`.

### SmolLM2 second-model qualification

The retained SmolLM2-1.7B-Instruct archive independently verifies. The model
answered 12/12 clean class-A cases and 0/12 clean class-B cases correctly, so
there were zero eligible attacks in either direction. The frozen behavioral
qualification failed and instrumentation correctly did not run. This is a
completed negative result, not evidence of second-model generalization.

### Real-Qwen Agent C

The retained development-only archive independently verifies all 48 rows with
zero invalid rows. Incoming accuracy was 0.5 and reviewed accuracy was 0.4375;
the paired difference was -0.0625 with bootstrap 95% interval
[-0.2708, 0.1458] and exact McNemar p=0.7011. The bundle's `PASS` denotes
integrity and completion only. No reviewer-improvement claim is supported.

### Real-Qwen red team

The retained attempt is not promoted. All 48 attempts were inference errors and
the hardened verifier rejects the zero-usable-denominator bundle even though an
older internal summary said PASS. It remains a visible failed attempt and no
red-team effectiveness claim is made.

## Deferred or externally blocked evidence

The project owner explicitly excluded new execution or retry work from this
local closure. The following therefore remain outside the completed evidence:

- BFCL official execution;
- MCPTox official execution;
- TAMAS official execution;
- a real-Qwen red-team rerun;
- another second-model attempt;
- another SAE design or training attempt.

Prepared runners are implementation artifacts, not benchmark evidence.

## Implementation state

The integrated Phase-1 system includes real-Qwen qualification and hooks,
paired trace capture, heterogeneous sender/message/receiver intervention,
cross-agent graph construction, greedy/beam/random/receiver-only/PPO searches,
graph-aware hierarchical RL, matched budgets and independent caches,
mechanism-guided remediation, locked validation, once-only testing, statistics,
strict verification/atomic ingestion, MCP transport, the review frontend and
fail-closed final reporting.

The review UI distinguishes successful evidence, terminal negative studies,
missing evidence and retained failed attempts. A final all-positive evidence
report is intentionally not generated while frozen prerequisites are unmet.

## Claim boundary

The repository supports an internal held-out causal-repair result on the frozen
balanced synthetic substrate. It does not establish an oracle-free defense,
clinical validity, population validity, global circuit minimality, a complete
distributed internal pathway, official benchmark performance or cross-model
generalization.
