# AETHER verified causal-core report

## Outcome

The frozen paired-clean-donor receiver L20H5 repair recovered attacked decisions on development-audit, locked-validation, and once-only-test cohorts of the frozen balanced synthetic task.

## Cohort results

| Cohort | Unique cases | Baseline attacked | L20H5 attacked recovery | Clean accuracy | Wilson 95% recovery | Exact McNemar p |
|---|---:|---:|---:|---:|---:|---:|
| development audit | 4 | 0.000 | 1.000 | 1.000 | [0.510, 1.000] | 0.125000 |
| locked validation | 8 | 0.000 | 1.000 | 1.000 | [0.676, 1.000] | 0.007812 |
| once only test | 8 | 0.000 | 1.000 | 1.000 | [0.676, 1.000] | 0.007812 |

Seeds 11, 22 and 33 are deterministic repetitions and are not treated as independent cases.

## Claim limits

- Does not establish oracle-free deployable defense.
- Does not establish clinical or population validity.
- Does not establish global circuit minimality.
- Does not establish complete distributed internal circuit.
- Does not establish second-model generalization.
- Does not establish official external benchmark performance.

## Remaining Phase-1 gates

- `bfcl_official`
- `mcptox_official`
- `tamas_official`
- `trained_sae_qwen_evaluation`
- `real_qwen_red_team`
- `real_qwen_agent_c`
- `second_model_qualification`
- `final_verified_report`
