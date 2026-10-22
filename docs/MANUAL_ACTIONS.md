# Manual Actions

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

## ACTION REQUIRED — MQ-HW1 memory cleanup

Close memory-heavy applications or reboot Windows, then rerun the same MQ-HW1 preflight. The frozen gate requires at least 10.5 GiB available physical RAM; the authorized retry measured only 1.487 GiB. No process was terminated automatically. Disk passed at 13.255 GiB free. Do not change the page file, install CUDA, lower the threshold, or access the model before the pre-access gate passes.

The 2026-10-19 recheck after cleanup improved available RAM to 2.814 GiB, but this remains below 10.5 GiB. A full Windows restart with minimal startup applications is still required before another unchanged pre-model check. If that cannot make 10.5 GiB available, finalize the Phase-1 pivot due to local compute constraints.
# Intermediate review manual actions — 2026-10-19

- Before presenting, run the commands in `docs/INTERMEDIATE_REVIEW_RUNBOOK.md` and verify ports 8000 and 5173 are free.
- Use `DEMO-PAT-001` for the primary escalation/attack/rescue story, `DEMO-PAT-002` for a DO_NOT_ESCALATE comparison, and a non-ECG case only if time permits.
- If live execution fails, select Verified Replay and disclose that provenance.
- Do not attempt Qwen2.5-1.5B MQ-HW1 until host-memory headroom satisfies the retry protocol. CUDA installation by itself is not the missing condition.
