# Demo Removal Contract

The dependency direction is strictly `demo -> AETHER core`. Research packages do not import `demo`.

After the intermediate review, the following may be removed together without damaging experiments:

- `demo/`
- `DEMO_README.md`
- `scripts/run_review_demo.ps1`
- `tests/unit/test_review_demo.py`
- `tests/integration/test_review_demo_e2e.py`
- the `demo` optional dependency group in `pyproject.toml`
- demo-specific sections of the intermediate-review documentation

Do not remove or rewrite AETHER core modules imported by the demo: `contracts`, `target`, `paired_trace`, `causal`, `instrumentation`, or committed scientific results. No demo condition, fixture ID, or UI dependency is present in those packages. The static boundary test fails if a core Python source begins importing `demo`.
