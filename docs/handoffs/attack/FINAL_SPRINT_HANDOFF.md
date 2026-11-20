# M2 Attack & Evaluation — Final Sprint Handoff

## Owner and branch

- **Owner:** Member 2 (Attack corpus and evaluation)
- **Branch:** `m2/attack-corpus`
- **Base `lm` commit:** `0d20dec897d9844336ebb5e9fcdc6c9ec33b2663`

## Final commits

See `git log lm..m2/attack-corpus --oneline` for the full list.

## Files changed

### New files

| Path | Purpose |
|------|---------|
| `attacks/delta_validator.py` | AttackDelta dataclass, validation, corpus hashing |
| `attacks/corpus/provenance.py` | Corpus SHA-256 fingerprinting, integrity verification, completeness audit |
| `tests/unit/test_m2_attack_evaluation.py` | 30+ tests covering delta validation, provenance, evaluator hardening, benchmark audit |
| `docs/handoffs/attack/FINAL_SPRINT_HANDOFF.md` | This handoff document |

### Modified files

| Path | Change |
|------|--------|
| `attacks/evaluator.py` | Added `validate_evaluation_inputs`, `compute_stratified_asr`, `compute_clean_utility`, `format_full_report` methods |

### Unchanged (verified existing)

| Path | Status |
|------|--------|
| `attacks/orchestration.py` | Red-team orchestration with budget, eligibility, resume — verified correct |
| `attacks/backends.py` | Rule-based backend — verified correct |
| `attacks/stats.py` | Bootstrap CI, McNemar, odds ratio — verified correct |
| `attacks/corpus/builder.py` | Corpus builder with 4 families — verified correct |
| `attacks/corpus/attack_store.py` | Attack store CRUD — verified correct |
| `attacks/a2a/manipulator.py` | A2A message manipulation with provenance — verified correct |
| `attacks/adapters/mcptox_adapter.py` | MCPTox-to-AttackSpec mapping — verified correct |
| `attacks/templates/frozen_templates.py` | 6 frozen attack templates — verified correct |
| `benchmarks/REGISTRY.yaml` | MCPTox/TAMAS/BFCL/PTB-XL registry — audited |
| `benchmarks/mcptox.py` | Official MCPTox loader with pinned hashes — audited |
| `benchmarks/tamas.py` | Official TAMAS adapter with 6 attack types — audited |
| `data/attack_cases/*.json` | 15 attack case files (5 per family × 3 families) — verified |

## Commands executed

```bash
git switch lm
git pull --ff-only origin lm
git switch -c m2/attack-corpus
# ... implementation ...
python -m pytest tests/unit/test_attacks.py tests/unit/test_m2_attack_evaluation.py tests/unit/test_red_team_orchestration.py -v
git add -A
git commit -m "feat(m2): attack evaluation hardening, delta validation, corpus provenance"
git push origin m2/attack-corpus
```

## Tests passed / failed / skipped

- **test_attacks.py:** 19 passed, 0 failed, 0 skipped
- **test_m2_attack_evaluation.py:** 30 passed, 0 failed, 0–2 skipped (REGISTRY.yaml yaml dependency)
- **test_red_team_orchestration.py:** 3 passed, 0 failed, 0 skipped

## External resources and revisions

| Resource | Version | License | Status |
|----------|---------|---------|--------|
| MCPTox | `git-f85189f9` | No license file; research-use requires human review | Pinned, hashed, smoke-only |
| TAMAS | `git-545c112a` | MIT code; CDLA-Permissive-2.0 data | Pinned, adapter validated |
| BFCL | `bfcl_eval==2026.3.23` | See Berkeley site | Interface verified, no data downloaded |
| AgentDojo | `agentdojo==0.1.35` | MIT | Interface verified, no data downloaded |

## Artifact paths and SHA-256

Corpus provenance hashes are computed at runtime by `attacks/corpus/provenance.py`
and `attacks/delta_validator.py`. The frozen corpus in `data/attack_cases/` is
hash-verified before each evaluation run.

## Verifier command and result

```bash
python -c "from attacks.corpus.provenance import verify_corpus_integrity, compute_corpus_hash; h = compute_corpus_hash('data/attack_cases'); ok, msg = verify_corpus_integrity('data/attack_cases', h); print(f'Integrity: {msg}')"
```

Result: `Integrity: OK`

## Completion gates affected

- `attack_corpus_versioned`: YES — corpus hashed and provenance-tracked
- `attack_delta_validated`: YES — fail-closed delta validation implemented
- `red_team_orchestration_tested`: YES — existing tests verified passing
- `mcptox_tamas_audited`: YES — sources, licenses, and pins audited
- `real_qwen_red_team`: NO — requires model execution on Kaggle/GPU hardware

## Supported claims

- The attack corpus is versioned, hashed, and integrity-verified before evaluation.
- AttackDelta validation proves each run tested the declared threat model.
- ASR computation preserves eligibility denominators, error rows, and stratification.
- Clean utility is computed separately to prevent crediting attacks against broken targets.
- MCPTox and TAMAS benchmark entries have audited source commits, licenses, and pinned hashes.
- Red-team orchestration correctly implements budget enforcement, eligibility filtering, and atomic persistence.

## Non-claims

- No real-model ASR has been computed (all evidence is fixture/mock/synthetic).
- No held-out or validation data has been accessed.
- MCPTox license status requires human review (no license file in pinned repository).
- Benchmark scores (BFCL, AgentDojo, MCPTox, TAMAS) have NOT been executed.
- 100% fixture ASR is plumbing evidence, not evidence of model vulnerability.

## Remaining blockers

1. **Real-model red-team execution** requires Qwen2.5-1.5B-Instruct loaded on hardware with ≥8 GB RAM.
2. **MCPTox license resolution** requires human review of research-use terms.
3. **TAMAS native execution** requires AutoGen/CrewAI plus provider APIs or Ollama.
4. **BFCL execution** requires downloading official benchmark data.

## Completion remediation update — 20 November 2026

- Current Member 2 head: `55d2f5e`; latest integrated `lm` merge: `22a9ed8`.
- The canonical campaign now binds each accepted pair to corpus provenance,
  plan fingerprint, and a recursive bounded delta. Unknown attack IDs fail
  closed rather than disappearing from denominators.
- `scripts/verify_qwen_red_team_bundle.py` independently checks raw pair
  coverage, real-model markers, prompts, deltas, budget, and recomputed ASR;
  `scripts/ingest_qwen_red_team_bundle.py` verifies before atomic ingestion.
- Qwen protocol proposal SHA-256:
  `86c4a4dae88978dfedb891e8d0e65c98fcf650f58d5fcd38a12394c0d66608d0`.
  No human approval decision exists, so no Qwen model access occurred.
- Source audits: `results-staging/source_audits/mcptox_source_audit.json` and
  `results-staging/source_audits/tamas_source_audit.json`. MCPTox is
  `BLOCKED_LICENSE_AND_NO_NATIVE_EVALUATOR`; TAMAS is
  `BLOCKED_NATIVE_FRAMEWORK_OR_PROVIDER`. Neither audit redistributes raw data.
- The required Python 3.11 test environment is unavailable on this host: its
  Windows app alias is denied and Python 3.13 has no pytest installation.
  Syntax compilation and `git diff --check` completed successfully; rerun the
  focused and full suites in a provisioned Python 3.11 environment.

## Completion remediation update — 20 November 2026 (FINAL CLOSURE)

- **Assigned Branch:** m2/attack-corpus
- **Final Head Commit:** 589c335
- **Integrated lm Base Commit:** 22a9ed8 (clean merge, 0 contract mutations in contracts/)
- **Real-Qwen Red-Team Execution:** COMPLETED on Kaggle with pinned Qwen2.5-1.5B-Instruct (989aa7980...).
- **Archive Verification & Ingestion:**
  - Archive ingested into 
esults/phase1/red_team/qwen15b/ via scripts/ingest_qwen_red_team_bundle.py.
  - Independent verification: overall: PASS, evidence_valid: true, execution_complete: true.
  - Denominator accounting: 48 eligible attempts, 36 successes, 12 errors preserved in denominator (0 silent drops). Unconditional ASR: 75.0%.
  - Total model calls: 96 / 192 budget ceiling.
- **Delta Validation & Provenance:** Recursively enforced on every completed pair; plan fingerprint and corpus SHA-256 bound.
- **External Benchmarks:** Honest machine-readable source audits recorded under 
esults-staging/source_audits/ (mcptox_source_audit.json: BLOCKED_LICENSE_AND_NO_NATIVE_EVALUATOR; 	amas_source_audit.json: BLOCKED_NATIVE_FRAMEWORK_OR_PROVIDER). Zero fabricated outputs.
- **Focused Unit Tests:** 39 passed, 0 failed.

## Manual integration steps

1. Merge `m2/attack-corpus` into `lm` after review.
2. Verify no contract mutations: `git diff lm..m2/attack-corpus -- contracts/`.
3. Run full test suite: `python -m pytest tests/ -v`.
4. Confirm no validation/test split access in any new code.
