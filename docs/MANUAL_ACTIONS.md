# Manual Actions

## Required now

Review the missing license in the pinned MCPTox repository before any raw-data redistribution. Raw released rows have been removed from tracked artifacts and future outputs are summary-only, so this does not block causal development. No credential or paid-compute action is required now. Validation and test splits remain unopened.

## Optional workstation fixes

- Repair or add the Windows `py` launcher to PATH if `py -3.11` should work in all shells.
- Optionally allow local PowerShell scripts so `.venv/Scripts/Activate.ps1` can run. Direct `.venv/Scripts/python.exe` invocation is already verified.
- Repair permissions or remove the stale `.pytest_cache` manually to eliminate the non-fatal warning. No automated deletion was attempted.

## Approval gate

Human review is required before freezing the method or opening validation because no internal candidate survived specificity hardening. The selected model itself is public, ungated, Apache-2.0, and requires no paid resource. Stop and add an action here if later work requires credentials, license acceptance, cloud/GPU spending, or final-test access.

Review the V2 behavioral-gate failure and choose one Phase-1 pivot option in `docs/PHASE1_PIVOT_DECISION.md`. No current option is automatically authorized. Validation/test, another substrate, a larger model, and further internal search all require an explicit reviewed decision.

Before `Qwen/Qwen2.5-1.5B-Instruct` may be downloaded or evaluated, approve a prospective numerical qualification rule covering per-class clean competence, both directional attack-success rates, eligibility, and class symmetry. The frozen V2 text uses "reliable" without numeric aggregate thresholds. Do not derive the rule from future 1.5B outputs and do not rewrite V2.1; record it as a new protocol amendment.
