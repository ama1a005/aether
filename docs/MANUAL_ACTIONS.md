# Manual Actions

## Required now

None. Stage 0 is ready for review.

## Optional workstation fixes

- Repair or add the Windows `py` launcher to PATH if `py -3.11` should work in all shells.
- Optionally allow local PowerShell scripts so `.venv/Scripts/Activate.ps1` can run. Direct `.venv/Scripts/python.exe` invocation is already verified.
- Repair permissions or remove the stale `.pytest_cache` manually to eliminate the non-fatal warning. No automated deletion was attempted.

## Approval gate

Approve the next bounded model-selection/non-interference task before any model or benchmark download.
