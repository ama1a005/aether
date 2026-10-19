# AGENTS.md — Coding-Agent Operating Rules for AETHER

## Mandatory Reading

Before editing ANY file, read:
1. `RESEARCH_CONTRACT.md` — novelty rules, metric definitions
2. `PROJECT_STATE.md` — current status, decisions, known bugs
3. `TASK.md` — current bounded task specification

---

## Architecture Invariants (NEVER violate)

1. **Contracts are frozen.** Never change a field name or type in `contracts/` without opening a schema-change issue and getting one other member approval.
2. **No hidden fallbacks.** Never silently catch errors or return fake/default outputs in production experiment paths.
3. **No fabricated results.** No AI-generated number may enter a result file unless it came from an executed experiment.
4. **One branch per owner.** Members: m1/target-harness, m2/attack-corpus, m3/mech-interventions, m4/cross-agent-graph.
5. **Logs are mandatory.** Every experiment run must save: run_id, UTC timestamp, git commit, dataset hash, model revision, seed, raw outputs.

---

## Prohibited Actions

- Do NOT modify `contracts/` casually
- Do NOT modify another member's primary directories
- Do NOT add `except Exception: pass` or similar silent swallowing
- Do NOT hard-code user paths (use config files)
- Do NOT embed model caches, activation tensors, or credentials in git
- Do NOT start new multi-hour features without a bounded TASK.md
- Do NOT fabricate experiment results or copy numbers manually into result files

---

## Test Commands

```bash
# Run all unit tests
python -m pytest tests/unit/ -v

# Run integration tests
python -m pytest tests/integration/ -v

# Run regression tests  
python -m pytest tests/regression/ -v

# P3 smoke test
python -m experiments.phase1.single_agent_circuit_smoke

# P4 smoke test
python -m experiments.phase1.cross_agent_smoke

# Full smoke test
bash scripts/smoke_test.sh
```

---

## Code Quality Standards

- Type hints on all public interfaces
- Dataclasses/Pydantic for data structures
- Deterministic configs via YAML
- No global hidden state
- Clear exceptions — never swallow errors
- Every public function has a docstring
- Structured logging with: `timestamp`, `run_id`, `experiment_id`, `component`, `event`, `payload`

---

## Experiment ID Convention

```
P0_<module>_<yyyymmdd>_<shortname>_<seed>

Examples:
P0_target_20261005_benign_smoke_0
P0_attack_20261006_mcptox_subset_0
P0_mech_20261007_greedy_ablation_0
P0_cross_20261007_message_patch_0
```

---

## Reproducibility Metadata (Required for every run)

```json
{
  "run_id": "...",
  "utc_timestamp": "...",
  "git_commit": "...",
  "uncommitted_diff": false,
  "dataset_manifest_hashes": {},
  "model_id": "...",
  "model_revision": "...",
  "tokenizer_revision": "...",
  "prompt_versions": {},
  "random_seeds": [],
  "hardware": "...",
  "python_env_hash": "...",
  "command_line": "...",
  "config_file": "...",
  "raw_output_path": "..."
}
```

---

## Standard Coding-Agent Prompt Template

> Read `AGENTS.md`, `RESEARCH_CONTRACT.md`, `PROJECT_STATE.md`, and this task specification completely before editing. Inspect the repository and tests. Implement only the requested module. Do not change public contracts or unrelated modules. Add/modify tests first where practical. Run the smallest relevant tests during iteration and the specified full test command before finishing. Do not fabricate experiment results. Do not silently catch errors or add fake fallback outputs. At the end, report changed files, tests run, remaining limitations, and any assumptions that need human review.

---

## PR Checklist

- [ ] Scope matches issue
- [ ] No contract change without approval
- [ ] Tests added/updated
- [ ] Tests pass
- [ ] No fake/mock output used in production experiment path
- [ ] Seeds/config logged
- [ ] No secrets
- [ ] README/docs updated if public behavior changes
- [ ] Research metric definitions unchanged or explicitly documented
- [ ] New experiment code writes manifest metadata
- [ ] One teammate reviewed

---

## Team Study Mode

When the user supplies `MEMBER_1_TARGET_PROTOCOL`, `MEMBER_2_ATTACK_EVALUATION`, `MEMBER_3_MECHANISTIC_INSTRUMENTATION`, or `MEMBER_4_CAUSAL_MEDIATION` and asks to study, review, or prepare, first read `Phase1Project.md`, `4_ProjectDescription.md`, `docs/team/COMPLETE_PROJECT_STUDY_GUIDE.md`, `docs/team/team_ownership.yaml`, and the matching member guide. Then inspect that member's current source files, tests, configs, and results as listed in the registry/guide. Teach the full project before the owned subsystem, and always include negative results and limitations.

Use `docs/team/team_ownership.yaml` as the ownership registry and `docs/team/COMPLETE_PROJECT_STUDY_GUIDE.md` as the shared conceptual baseline. Each member must study the matching `MEMBER_*` guide, but ownership never excuses ignorance of the full pipeline. Ownership tags are review responsibilities, not claims of Git authorship.

Study answers must cite repository paths and distinguish four things: code behavior, test evidence, executed experimental evidence, and future work. Codex may explain or quiz from checked-in sources, but it must not invent metrics, reconstruct missing outputs, or describe development evidence as validation. Any disagreement between a study guide and a frozen contract is resolved in favor of `RESEARCH_CONTRACT.md` and must be corrected in the guide.
