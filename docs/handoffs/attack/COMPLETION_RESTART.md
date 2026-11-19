# Member 2 completion restart

## Integrated baseline

- Branch: `m2/attack-corpus`
- Integrated `lm`: `449d607 Complete Member 4 causal-core reporting and demo`
- Merge commit: recorded in this branch before the implementation repairs.
- Protected causal-core evidence was preserved and `contracts/` has no changes.

## Local environment

- Active interpreter: Python 3.13, without `pytest`.
- Registered Python 3.11 app alias: access denied by the host, so the required
  Python 3.11 environment could not be created or used here.
- Focused test command has not run in this environment for that reason.
- Syntax compilation and `git diff --check` ran successfully after the local
  implementation changes.

## External readiness

- Qwen protocol approval: missing. The protocol config was expanded and must
  receive a new exact-hash human decision before any snapshot access.
- MCPTox source checkout/licence decision: unavailable; official execution is
  blocked pending a defensible licence decision and native evaluator audit.
- TAMAS source checkout/native framework/provider: unavailable; official
  execution is blocked pending a supported framework and provider.

No Qwen, validation, test, MCPTox, or TAMAS model execution occurred during
this restart.
