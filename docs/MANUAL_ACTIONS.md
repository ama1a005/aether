# Manual Actions

## 2026-11-13 — run the CORE-02 matched-search notebook

Upload `notebooks/aether_qwen_core02_matched_search.ipynb` to Kaggle, enable
Internet, choose a CPU session with at least 12 GiB available RAM, and run all
seven cells. The notebook pins commit
`67759734dc841ddd5b0705d5846cb396408e9b84` and executes five methods across
seeds 11, 22 and 33 on development-discovery only.

After every completed mask evaluation it replaces
`/kaggle/working/aether-core02-checkpoint.tar.gz`. If the session ends, download
that file, upload it as a private Kaggle dataset/input, start a new session with
the same notebook and run all cells again. Attach exactly one checkpoint.

When successful, download `aether-core02-results.tar.gz`, extract it under
`notebooks/Results/core02`, and retain the archive itself. Do not modify the
notebook, masks, methods, seeds, budgets or protected splits.

## 2026-11-13 — QCI-2 audit complete; no rerun required

The returned QCI-2A1 archive independently verifies and has been ingested. All
four candidates replicated across the untouched development-audit cases, with
168 valid executions and no validation/test access. Do not rerun or modify the
audit notebook. No manual action is currently required while the search and
remediation method is frozen and model-free verified. A new commit-pinned
notebook and explicit instructions will be supplied before any next retained
model execution.

## 2026-11-13 — QCI-2 audit is now authorized

QCI-2 discovery independently verified with four supported candidates and
returned `ELIGIBLE_TO_FREEZE_QCI2_DEVELOPMENT_AUDIT`. Upload
`notebooks/aether_qwen_qci2_semantic_audit_cpu.ipynb` and attach the successful
`aether-qwen-qci2-results.tar.gz` as one private Kaggle input. Run all cells
once on CPU with Internet enabled. Do not alter candidates, thresholds, cases,
operators or budgets, and do not open validation/test. Download and preserve
`aether-qwen-qci2-audit-results.tar.gz` regardless of the audit outcome.

## 2026-11-12 — execute the prospectively frozen QCI-2 notebook once

After the notebook commit is pushed to branch `lm`, upload
`notebooks/aether_qwen_qci2_semantic_cpu.ipynb` to Kaggle. Enable Internet,
select a CPU session with at least 12 GiB available RAM, and run all cells once.
The corrected notebook pins runner commit
`3faae014ff839f7e39c7403ef2810f779595b709`. The first upload stopped in
model-free verification before preflight/model access because gitignored QCI-1
logs were absent from the clean checkout; it is not a scientific attempt. GPUs remain unused to preserve
the qualified CPU-float32 condition.

Do not change donors, candidates, thresholds, cases, or budgets; do not delete
the marker to rerun; and do not open audit, validation, or test. Download
`aether-qwen-qci2-results.tar.gz`. Do not use the old QCI-A1 notebook for QCI-2.

## 2026-11-12 — QCI execution complete; do not run the audit notebook

QCI-1.1 was verified and ingested. Its binding outcome is
`STOP_NO_SUPPORTED_CANDIDATE`: none of the 12 candidates passed the frozen
specificity rule. Do **not** run `aether_qwen_causal_audit_cpu.ipynb`, loosen
thresholds, replace candidates from observed effects, or open validation/test.
The next manual action is a research-review decision about reporting the
negative result or prospectively defining a new study; it is not a rerun.

## 2026-11-11 — execute frozen QCI-1.1 on Kaggle

Upload `notebooks/aether_qwen_causal_interventions_cpu.ipynb` from branch `lm`.
Confirm that it has 11 cells and pins source commit
`0e8a616aedd8a7a5caf2af5b34d9170bf9f114fc`. Enable Internet and run all cells
once. Do not interrupt the 1,344-execution intervention cell, delete its marker,
change candidates/thresholds, or open development-audit, validation, or test.
Download `aether-qwen-qci-results.tar.gz` and retain any failed archive. This is
the current external-compute dependency; the local preflight correctly blocks
on available RAM before model access.

After extracting the archive, ingest it with the fail-closed verifier (choose a
new destination; existing evidence is never overwritten):

```powershell
.\.venv\Scripts\python.exe scripts\ingest_qci_bundle.py <extracted-folder> results\phase1\causal_interventions\qwen15b_qci1 --archive <archive-path>
```

Only if that command's verification report says
`ELIGIBLE_TO_FREEZE_DEVELOPMENT_AUDIT`, attach the same retained discovery
archive as a private Kaggle input and run
`notebooks/aether_qwen_causal_audit_cpu.ipynb`. It pins source commit
`8d5e5d3f30de0b3df2e443b31afca90073fa1d6e`. If the discovery report says
`STOP_NO_SUPPORTED_CANDIDATE`, do not run the audit notebook.

## Kaggle Qwen2.5-1.5B instrumentation acceptance — 2026-11-11

The qualification archive has been ingested and its inner artifacts verified.
After the IA-G1 notebook is committed, upload
`notebooks/aether_qwen_instrumentation_acceptance_cpu.ipynb` to a private Kaggle
notebook with Internet enabled and run it once from top to bottom. GPU is not
used because IA-G1 preserves the qualified CPU-float32 condition. Download and
preserve `aether-qwen-instrumentation-acceptance-results.tar.gz` regardless of
PASS or failure. Do not delete the attempt marker, tune selected sites/cases, or
rerun after model access. Do not open validation/test.

## No manual action for the probe-baseline milestone

The correlational probe implementation and synthetic acceptance are CPU-light.
The real activation-probe experiment must wait for an approved, qualified model
run and prospectively selected activation features; do not manually copy arrays
or metrics into result files.

## 2026-10-22 — tests on the higher-memory laptop

Checkout branch `lm`, create the Python 3.11 environment, and install the locked
dependencies. Run the model-independent portable suite with:

```powershell
.\scripts\run_other_laptop_checks.ps1
```

If the pinned Qwen2.5-0.5B and GPT-2 snapshots from their registries are present,
add `-IncludeQwen05Tests -IncludeGPT2Tests`. Check the larger-model resource gate
with `-CheckMQHW1 -CacheDrive <model-cache-drive>`; failure writes
`.local/portable-mq-hw1.json` and performs no model access.

The frozen files name Qwen2.5-1.5B but do not pin its exact repository revision.
Do not download or execute it merely because the hardware gate passes. Freeze
the revision and snapshot provenance prospectively before the single authorized
model-access campaign. Validation and test splits remain locked.

## 2026-10-21 current action

The demo is running at `http://127.0.0.1:8000/?mode=mock_deterministic` in explicit
mock mode. No RAM upgrade or CUDA reinstall is justified by the observed transport
failure. Host MCP SDK is now installed; the older missing-wheel gate below is
historical. External mode still requires diagnosing the host-to-Docker malformed
chunked response. A Docker Desktop restart would affect other workloads and has
not been performed; save those workloads before choosing that diagnostic step.
Do not disable security software or TLS verification. Qwen qualification remains
a separate task. See `RELIABILITY_CHECKPOINT.md`.

## 2026-10-20 — external MCP host dependency

To clear the final gate, provide a verified Windows/Python 3.11 wheelhouse for `mcp[cli]==1.27.1` and dependencies, or fix the proxy path producing `InvalidChunkLength`. Docker Desktop must run. Do not disable TLS verification. The WSO2 image currently relies on ARM64 emulation.

## 2026-10-19 — demo GPU environment blocked by package-download proxy

The first download attempt failed TLS certificate validation. Pip's verified Windows trust-store mode fixed that, but repeated PyPI transfers then failed with `InvalidChunkLength`, indicating a proxy/network response corruption. CUDA and the RTX 2050 are visible. Do not bypass verification with `--trusted-host`.

### Stable network option

From a Windows x86-64 machine with Python 3.11 and a trusted stable connection, use the same repository checkout:

```powershell
.\scripts\build_demo_wheelhouse.ps1 -Wheelhouse .local\wheelhouse
```

This downloads ordinary dependencies from PyPI, `mcp==2.3.0`, and only `torch==2.8.0` from the official CUDA 12.6 PyTorch index. It creates SHA-256 `wheelhouse_manifest.json`. Do not add torchvision or torchaudio.

### Offline wheelhouse option

Transfer the entire `.local\wheelhouse` directory by USB, trusted cloud storage, or local network to this repository's `.local\wheelhouse`, then run:

```powershell
.\scripts\install_demo_wheelhouse.ps1 -Wheelhouse .local\wheelhouse
.\.venv-demo-gpu\Scripts\python.exe -m pytest tests\integration\test_demo_mcp_stdio.py -v
.\.venv-demo-gpu\Scripts\python.exe scripts\download_demo_model.py
.\.venv-demo-gpu\Scripts\python.exe scripts\verify_demo_model_cache.py
.\.venv-demo-gpu\Scripts\python.exe scripts\accept_demo_model.py
.\.venv-demo-gpu\Scripts\python.exe scripts\qualify_demo_live.py
```

If Hugging Face is also unreliable, run `download_demo_model.py` on the stable machine, transfer the exact snapshot directory containing `aether_model_snapshot_manifest.json`, set `AETHER_DEMO_MODEL_PATH` to that directory here, and start at `verify_demo_model_cache.py`. Do not transfer an unknown whole Python environment.

Until the qualification succeeds, live Qwen + MCP is implemented but not verified or accepted.

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

MQ-G1 is now approved and frozen. The 1.5B run remains blocked because only 1.66 GiB physical RAM was available at preflight. If qualification should be retried, close unrelated memory-heavy applications or reboot, then explicitly authorize rerunning the same frozen MQ-G1/MQ-G2 task. Do not modify paging automatically, install CUDA, alter thresholds, or change prompts.

## Historical blocked actions — superseded by the Kaggle action below

The Windows-only MQ-HW1 cleanup instructions below describe the 2026-10-16/19
local preflight attempts. They are retained as history and are no longer the
current next step; use the Kaggle instructions at the end of this file.

### Windows MQ-HW1 memory cleanup record

Close memory-heavy applications or reboot Windows, then rerun the same MQ-HW1 preflight. The frozen gate requires at least 10.5 GiB available physical RAM; the authorized retry measured only 1.487 GiB. No process was terminated automatically. Disk passed at 13.255 GiB free. Do not change the page file, install CUDA, lower the threshold, or access the model before the pre-access gate passes.

The 2026-10-19 recheck after cleanup improved available RAM to 2.814 GiB, but this remains below 10.5 GiB. A full Windows restart with minimal startup applications is still required before another unchanged pre-model check. If that cannot make 10.5 GiB available, finalize the Phase-1 pivot due to local compute constraints.
# Intermediate review manual actions — 2026-10-19

- Before presenting, run the commands in `docs/INTERMEDIATE_REVIEW_RUNBOOK.md` and verify ports 8000 and 5173 are free.
- Use `DEMO-PAT-001` for the primary escalation/attack/rescue story, `DEMO-PAT-002` for a DO_NOT_ESCALATE comparison, and a non-ECG case only if time permits.
- If live execution fails, select Verified Replay and disclose that provenance.
- Do not attempt Qwen2.5-1.5B MQ-HW1 until host-memory headroom satisfies the retry protocol. CUDA installation by itself is not the missing condition.

## Kaggle Qwen2.5-1.5B qualification — 2026-11-10

1. Upload `notebooks/aether_qwen_qualification_cpu.ipynb` to a private Kaggle notebook and enable Internet. GPU is not required; if T4 GPUs are attached, this frozen run intentionally does not use them.
2. Run the cells from top to bottom once. Do not edit the model revision, thresholds, prompt, seed, or dataset. MQ-HW1 must pass before the model-download cell.
3. Preserve `aether-qwen-qualification-results.tar.gz` from Kaggle outputs. The archive includes the preflight, snapshot hash manifest, attempt marker, gate results, raw per-case rows, environment inventory, and logs. Do not reset the attempt marker or rerun after model access begins.
4. If the preflight blocks, stop before model access. If the model load or qualification fails, preserve the failure and do not tune/retry. MQ-G2 is skipped unless MQ-G1 passes.
5. If MQ-G1 and MQ-G2 both pass, stop and review the evidence before authorizing a separate instrumentation-acceptance task. This notebook does not produce internal causal-circuit evidence.
