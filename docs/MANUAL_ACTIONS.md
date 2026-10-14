# Manual Actions

## Required now

None. The mechanistic calibration checkpoint is ready for review.

## Optional workstation fixes

- Repair or add the Windows `py` launcher to PATH if `py -3.11` should work in all shells.
- Optionally allow local PowerShell scripts so `.venv/Scripts/Activate.ps1` can run. Direct `.venv/Scripts/python.exe` invocation is already verified.
- Repair permissions or remove the stale `.pytest_cache` manually to eliminate the non-fatal warning. No automated deletion was attempted.

## Approval gate

No approval is currently blocking: the selected model is public, ungated, Apache-2.0, and requires no paid resource. Stop and add an action here if later work requires credentials, license acceptance, cloud/GPU spending, or final-test access.
