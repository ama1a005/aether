# Reliability checkpoint — 2026-10-21

## Verdict

The explicit mock review demo works in the checks below. The **whole project is
not certified flawless**: real external WSO2 host transport is still blocked,
Qwen-over-FHIR is unqualified, and remote CI has not run.

## Executed checks

| Check | Observed result |
|---|---|
| Python | Repository `.venv`, Python 3.11.9 |
| Complete `pytest` suite | 196 passed, 0 failed, 5 skipped (201 collected) |
| Opt-in model-free demo E2E | 2 passed, separately enabled |
| `scripts/smoke_test.py` | 3/3: unit tests, P3, P4 |
| Regression command smokes | P1, P2, P3, P4 and E2E passed within pytest |
| Frontend | 4 tests passed; TypeScript/Vite production build passed |
| Dependency consistency | `pip check`: no broken requirements |
| Updated launcher | Occupied-port rejection verified; identified old demo restarted; new instance health verified |
| HTTP UI/API | Root page 200; health identifies service/process; 12 cases loaded |
| Mock HTTP actions | 48/48: clean, attack, rescue, induction for every case; clean correctness and rescue recovery checked |
| Real local stdio MCP | SDK integration test passed, including real subprocess tool discovery/calls |
| External WSO2 host discovery | Failed: malformed chunk framing; bounded failure rather than indefinite wait |
| External WSO2 in-container initialization | 200, valid Content-Length and initialize JSON |

The five default skips are two Qwen hook tests, one GPT-2 calibration test and
two opt-in demo E2E tests. The latter two passed when explicitly enabled. No
model was downloaded or loaded for this checkpoint. Frontend verification is
component interaction tests plus production build and HTTP serving, not a full
visual/browser acceptance run.

Commands:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp .local/test-reliability-final
$env:AETHER_RUN_DEMO_E2E='1'
.\.venv\Scripts\python.exe -m pytest tests/integration/test_review_demo_e2e.py -q -p no:cacheprovider
.\.venv\Scripts\python.exe scripts/smoke_test.py
.\.venv\Scripts\python.exe -m pip check
# In demo/frontend: npm.cmd test; npm.cmd run build
```

## Confirmed fixes

- Legacy stdio client/server migrated to actual MCP 1.27.1 `ClientSession`,
  `stdio_client`, FastMCP and camel-case result fields.
- External MCP calls have session and overall deadlines with useful error detail.
- Real-FHIR induction implemented; rescue/induction persist results linked to
  their prerequisite runs and use a single retrieval snapshot.
- Missing, duplicate or non-boolean risk evidence is rejected. Invalid bundles,
  paginated partial results and wrong Patient identity are rejected.
- Attack modifies exactly one adapted field; raw resources remain untouched.
- Unknown pipeline cases return 404; optional Qwen tools cannot silently use
  mock retrieval; unqualified Qwen execution remains 503 and its UI option is disabled.
- Boolean attack values are visible. UI exposes all three evidence layers and
  describes deterministic substitution without claiming neural causality.
- Launcher serves built UI/API together, checks port ownership, records logs,
  verifies its own instance and checks seeding/MCP readiness. Vite dev port is strict.
- HTTP requests are bounded; startup metadata errors are surfaced; mode changes
  and navigation are disabled during an active operation.
- Fixture birth dates are anchored to the fixed 2026 demo reference year.
- Added observed Windows demo dependency pins and CI coverage for demo/UI.

## Remaining boundaries

1. **External transport:** host curl/Python/PowerShell fail whereas in-container
   HTTP is valid. WSO2 restart did not fix it. Exact host/Docker intermediary is
   unresolved; a Docker Desktop-wide restart needs user coordination because it
   affects other workloads. No RAM or CUDA change is supported by this evidence.
2. **Qwen:** unqualified; mock correctness is not model correctness. No new
   scientific result, model download or frozen contract change was made.
3. **CI/install:** workflow updated, but remote CI and a fresh clean install were
   not executed. Dependency snapshot records the tested existing environment.
4. **Scope:** FHIR pagination is deliberately rejected rather than silently
   truncated. Synthetic risk evidence encodes a fixture rule, not clinical validity.
5. **Test isolation:** historical regression smokes rewrite tracked artifacts.
   This run's generated copies are preserved under `.local/reliability-smoke-backup`;
   their clean tracked originals were restored. Future isolation remains technical debt.

## Try the verified demo

Current server: `http://127.0.0.1:8000/?mode=mock_deterministic`.
Choose a case, run Clean Pipeline, then Controlled Attack, then rescue/induction
in Causal Analysis. External FHIR discovery is separate and remains blocked.

Restart with `./scripts/run_review_demo.ps1 -Mode mock_deterministic` after
stopping the previous demo PID printed by the launcher. Do not kill unidentified
Python processes. The default real-MCP launcher fails closed while its handshake fails.
