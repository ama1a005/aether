# M4 final-sprint handoff: causal core and protected evaluation

## Ownership

- Owner: Member 4, cross-agent causal mediation
- Owner branch: `m4/cross-agent-graph`
- Integration branch used by the project owner: `lm`
- Primary paths: `causal/`, `experiments/phase1/`, protected evaluation,
  evidence registries, causal-core reporting and integration

## Completed scientific sequence

1. QCI-1 was retained as a negative result for case-specific mediation.
2. QCI-2 semantic discovery and audit supported four semantic candidates.
3. CORE-02 compared greedy, matched random, beam, flat PPO and receiver-only
   search. Distributed methods retained `message.decision_code`; receiver-only
   retained `receiver.head.L20.H5.pre_o_proj`.
4. CORE-03 selected the receiver L20H5 repair under its frozen ordering.
5. CORE-04 evaluated that unchanged repair on eight locked validation cases.
6. CORE-05 evaluated it in one retained attempt on eight locked test cases.

## Retained outcomes

| Stage | Outcome | Rows | Forwards | Protected access |
|---|---|---:|---:|---|
| CORE-02 | COMPLETE | 220 mask evaluations | recorded per method | audit 0, validation 0, test 0 |
| CORE-03 | SELECTED_DEVELOPMENT_REPAIR | 120 | 624 | validation 0, test 0 |
| CORE-04 | VALIDATION_ACCEPTED | 96 | 504 | test 0 |
| CORE-05 | TEST_ACCEPTED | 96 | 504 | one test attempt |

For CORE-04 and CORE-05, L20H5 attacked recovery was 1.0 and no-defense
recovery was 0.0 for seeds 11, 22 and 33. Clean decision accuracy was 1.0 and
invalid/error count was zero. Seeds are deterministic repetitions, not
independent observations. Unique-case exact McNemar p-values are 0.0078125 for
validation and test; the Wilson 95% interval for 8/8 is approximately
[0.6756, 1.0].

## Evidence and archive hashes

- CORE-03 final archive: `eff5fbc3316e1f38c46bf6ff9b848368532f295fc29bd4a5871871ba0bc1efb5`
- CORE-04 final archive: `71ab9429204b29f98c46273e4696f0cbc6a6f27673bb49b8f701055472ab980d`
- CORE-05 final archive: `820c9e0b9ddcbf023ccb26767e162faede4626c39cd141e68d9ce6ebb591f733`
- CORE-05 attempt ID: `d25c770d-9159-4114-8dfa-7eee8c8618bd`
- Official directories: `results/phase1/search_comparison`,
  `results/phase1/remediation`, `results/phase1/locked_validation`, and
  `results/phase1/once_only_test`
- Derived verified report: `results/phase1/causal_core_report`

## Independent verification

```powershell
python -m scripts.verify_qci2_matched_search_bundle results/phase1/search_comparison
python -m scripts.verify_core03_remediation_bundle results/phase1/remediation
python -m scripts.verify_core04_validation_bundle results/phase1/locked_validation
python -m scripts.verify_core05_test_bundle results/phase1/once_only_test
python scripts/phase1_execution_status.py
```

## Final local verification

- Unit: 620 passed, 0 failed, 0 errors, 0 skipped.
- Integration plus regression: 24 passed, 0 failed, 5 skipped because their
  declared real-model/demo runtime prerequisites were unavailable.
- Frontend: 5 passed across 2 test files.
- Frontend production build: passed, 35 modules transformed.
- P3 single-agent circuit smoke: passed.
- P4 cross-agent graph smoke: passed.
- Aggregate smoke wrapper: completed after rerunning unit, P3 and P4 checks.

## Supported claim

On the frozen balanced synthetic AETHER task and pinned Qwen2.5-1.5B-Instruct
revision, the prospectively selected paired-clean-donor receiver L20H5 patch
recovered attacked decisions on development-audit, locked-validation and
once-only-test cohorts while preserving clean decisions.

## Required non-claims

The evidence does not establish an oracle-free deployable defense, clinical or
population validity, global circuit minimality, a complete connected internal
DCMG, second-model generalization, official external benchmark performance, or
independent statistical replication from deterministic seed repetition.

The task can encourage decision-code copying. Message-field sufficiency and
L20H5 repair do not by themselves prove a complete adversarial trust mechanism.

## Integration state

The completion registry recognizes remediation, locked validation and once-only
test as complete. Overall Phase 1 remains incomplete because BFCL, official
MCPTox/TAMAS, trained SAE, real-Qwen red team, Agent C, second-model
qualification and the all-evidence final report remain missing or blocked.

## Manual integration steps

1. Review M1-M3 branches against `RESEARCH_CONTRACT.md`.
2. Verify every external bundle before ingestion.
3. Never rerun CORE-05.
4. Regenerate derived reports only from verified artifacts.
5. Generate the all-project final report only after every configured
   prerequisite passes or is formally not applicable under an approved rule.

## Presentation assignment

M4 explains candidate graphs, interventions, message versus receiver mediation,
matched search, split isolation, CORE-03/04/05, exact claim limits, the oracle
donor, the QCI-1 negative result and why deterministic seeds are not independent.
