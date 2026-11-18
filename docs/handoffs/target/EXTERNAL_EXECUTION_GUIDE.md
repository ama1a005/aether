# AETHER Member 1 external execution guide

This guide covers only BFCL and the Agent C supporting experiment. **Do not
start either run until the corresponding human approval is recorded.** No
approval artifact is currently present. No experiment has been run as part of
preparing this guide.

## At a glance

| Experiment | Run on this Windows laptop? | Recommended environment | Why |
|---|---:|---|---|
| Official BFCL | No, not under the pinned runner | Linux GPU Pod with an explicitly selected T4/A10/L4/RTX 4090 class device; Kaggle only if it actually supplies a compatible GPU | The canonical BFCL profile invokes vLLM on CUDA and verifies the full pinned Qwen snapshot. The laptop has no CUDA/NVIDIA GPU; vLLM is Linux-oriented and current CUDA wheels require compute capability 7.5+. |
| Qwen Agent C development review | Yes, CPU is suitable | Local Windows, in a clean clone/worktree after approval | This is not another Qwen inference run. It applies frozen deterministic Agent C to the 24 retained real-Qwen A/B development rows, reviewing clean and attacked conditions (48 case-condition rows). It does not load model weights. |

The checked-out host reports Windows 10, Python 3.11.9, 15.67 GiB RAM, CPU-only PyTorch (`torch.cuda.is_available() == False`), zero CUDA devices, and about 308 GiB free on C:. Your Intel i7-13620H and integrated graphics do not provide an NVIDIA CUDA device. Agent C's retained input files are about 0.23 MiB (rows) and 0.03 MiB (case registry); the deterministic runner needs only Python and PyYAML, not Torch or Transformers. BFCL's retained Qwen snapshot is 2.89 GiB across 10 files, before runtime/dependency/data storage.

CPU-only BFCL would require changing the pinned vLLM execution backend or rewriting the adapter to use a different inference stack. That would no longer be the approved canonical run. Do not use WSL/CPU or replace vLLM with a mock. vLLM documents Linux as its OS requirement, no native Windows support, and current NVIDIA GPU support from compute capability 7.5 (including T4, A100, L4); the vLLM wheel installation is sensitive to CUDA/PyTorch compatibility. See [vLLM installation requirements](https://docs.vllm.ai/en/stable/getting_started/installation/gpu/) and [installation quickstart](https://docs.vllm.ai/en/stable/getting_started/quickstart/).

The repository has a Kaggle-ready notebook, but a Kaggle GPU is only suitable if the assigned card passes the preflight. Kaggle documents a free single Tesla P100 option and GPU availability/quota limits; a P100 has compute capability 6.0 and is rejected by the current vLLM CUDA requirements. Treat Kaggle as a convenient option only when Settings actually offers a T4 or newer compatible card. For reliability, the recommended BFCL environment is a Linux GPU Pod where you explicitly select T4/A10/L4/RTX 4090. Kaggle documents GPU selection in Notebook Settings and notes availability/quota limits ([Kaggle notebook setup](https://www.kaggle.com/docs/notebooks), [GPU usage](https://www.kaggle.com/docs/efficient-gpu-usage)). If Kaggle cannot supply a compatible GPU, use a Linux GPU Pod where you can explicitly select a T4 (16 GiB), A10/L4 (typically 24 GiB) or RTX 4090 (24 GiB). For example, RunPod's Pod deployment flow allows GPU type, disk, volume and exposed ports to be selected ([Pod documentation](https://docs.runpod.io/runpodctl/reference/runpodctl-remove-pods)). Cloud GPU time/storage may be billable; review the provider's current prices and stop/terminate the resource after downloading the archive.

## Human approval gates

### BFCL approval

The human reviewer must read [BFCL approval instructions](BFCL_APPROVAL_INSTRUCTIONS.md), the frozen [BFCL config](../../../configs/benchmarks/phase1_external.yaml), the [BFCL runbook](../../benchmarks_nov19/BFCL_RUNBOOK.md), and this guide's BFCL claim boundary. The reviewer approves the exact config bytes (SHA-256 `017bce07725a36ed4f7d8f08b399a22c1b4092271c2ce2473b2fd138b5e4ff75`), official BFCL evaluator with a disclosed AETHER adapter, the fixed four categories, Qwen model/tokenizer revision, denominators, development-only scope, and the Linux/CUDA requirement. They must not authorize validation/test.

Only the authorized human creates `results/phase1/protocol_approvals/bfcl_official.json` with their name and the exact schema/hash shown in the approval instructions. Do not create this file until approval is granted. Commit/push that decision alone, then repin the notebook to the new source commit as shown below. The runner refuses to access the model without it.

### Agent C approval

The human reviewer must read `results/phase1/protocol_approvals/HUMAN_APPROVAL_INSTRUCTIONS.md` and the complete [frozen Agent C proposal](../../../configs/experiments/agent_c_qwen_development.yaml). Confirm this is **retained real-Qwen A/B traces plus deterministic clean-tool Agent C review**, not a third Qwen model. Review the 24 declared development IDs, paired clean/attacked conditions, fixed threshold, recorded inputs/tool calls/errors, supporting-evidence-only claim, and zero validation/test executions. The proposal's exact SHA-256 is `211ff7d3cc78ab962b5b9bf9c478484c656e6ede06ab8be9427a1a05151fef5b`.

Only the authorized human creates and commits `results/phase1/protocol_approvals/agent_c_qwen_development.json` with their real reviewer name, that exact proposal hash, `approved: true`, and both protected-split flags `false`. Do not edit the proposal to make approval pass. The local runner fails before opening trace data if approval is absent or mismatched.

## Part A ? Official BFCL on a Linux GPU

### A1. Prepare the reviewed notebook on Windows

Run these commands in **PowerShell**, from your AETHER checkout. The existing working changes are safe; these commands stage only the approval and notebook files named below.

After the human reviewer has created the BFCL decision file:

```powershell
Set-Location C:\Users\ardra\aether
Get-FileHash configs\benchmarks\phase1_external.yaml -Algorithm SHA256
Get-Content results\phase1\protocol_approvals\bfcl_official.json
```

Confirm the config hash matches the value above and the approval JSON contains the human reviewer's real name. Then commit only the approval artifact:

```powershell
git add results/phase1/protocol_approvals/bfcl_official.json
git commit -m "chore(bfcl): record human protocol approval"
git push origin m1/target-harness
$sourceCommit = (git rev-parse HEAD).Trim()
python scripts/build_kaggle_official_benchmark_notebook.py bfcl --commit $sourceCommit --output notebooks/aether_bfcl_official.ipynb
git add notebooks/aether_bfcl_official.ipynb
git commit -m "docs(bfcl): pin approved execution notebook"
git push origin m1/target-harness
```

These commands do not stage or alter your other pre-existing changes. If Git says
there are no changes to commit, stop and check whether the approval file was
created by the authorized reviewer and is untracked at that path. Do not use an
approval from another config hash.

### A2. Optional Kaggle route (only if its GPU is compatible)

1. Sign in at [Kaggle](https://www.kaggle.com/) and open **Code / Notebooks**.
2. Choose **New Notebook**. In the notebook editor use **File ? Import Notebook** (or the upload/import button shown by the editor) and upload `notebooks/aether_bfcl_official.ipynb` from your Windows checkout. Do not use an older downloaded copy.
3. Open the right-side **Settings** panel. Set **Accelerator ? GPU** and enable **Internet**. Save/apply; the session may restart.
4. Confirm the notebook's `COMMIT` equals the source commit used by its builder. Click **Run All** only after the approval file has been committed and pushed.
5. The notebook installs the repository lockfile, downloads and hash-checks the exact BFCL wheel, installs vLLM with the CUDA backend selected by `uv`, verifies approval and hardware, then verifies the qualified Qwen snapshot before official model access. Its preflight must report CUDA available, at least one GPU with at least 16 GiB and compute capability 7.5+, and an installed `vllm` backend. If it reports a P100/compute capability 6.0, insufficient memory, missing vLLM or any other failure, stop; do not try a CPU workaround. Use Part A3.
6. The official run may take a long session and downloads about 2.89 GiB of pinned model files plus environment and benchmark files. Keep the session alive, do not alter cells/config/categories, and do not click Run All twice. The notebook uses an `attempt-1` output name and refuses to overwrite a previous output. If a run stops or fails, retain and download its evidence bundle; a failed/blocked summary is not a score. To retry, set `AETHER_BFCL_ATTEMPT` to a new unique value (for example `attempt-2`) in the notebook's first cell, rerun all cells in a fresh runtime, and retain both attempts. The official runner has no partial-generation resume mode; do not reuse or edit a partial output.

### A3. Recommended reliable route: Linux GPU Pod

Use this route when you want to select a known-compatible GPU explicitly, or if Kaggle preflight cannot obtain one. A Pod is an external, potentially billable machine; no resource is created by this guide.

1. In the provider console open **Pods ? Deploy a Pod**. Choose a Linux/PyTorch CUDA template, select one GPU explicitly (T4 16 GiB or larger, compute capability 7.5+; A10/L4/RTX 4090 are suitable classes), set at least 30 GiB container disk and 30 GiB persistent volume, and expose the Jupyter port shown by the selected template (commonly 8888). Review the current price before deploying. The exact current availability depends on provider/region.
2. Open the template's JupyterLab link. Upload `notebooks/aether_bfcl_official.ipynb` from Windows. The notebook uses `/kaggle/working` on Kaggle and a local `aether-execution-output` folder when that Kaggle path is absent.
3. Verify the notebook `COMMIT`, then use **Run ? Run All Cells**. The same fail-closed preflight applies. Stop the Pod when finished downloading the verified archive.

The benchmark's pinned runner needs Linux, CUDA, compatible PyTorch/vLLM wheels, vLLM, 16 GiB minimum GPU memory, the official BFCL package wheel, and the complete pinned Qwen model/tokenizer snapshot. The source setup uses Python 3.11.9 and records the installed Python environment hash. The official BFCL wheel is `bfcl_eval==2026.3.23`, SHA-256 `3bb6dfa5f0c68ad403c9ec50b00db2bb3b4cc9b38ab1ff33f48fe30d853d3a0a`; the model/tokenizer revision is `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`.

### A4. Expected result and verification

Successful execution prints the output archive path and its SHA-256. The default archive is `aether-bfcl-official-attempt-1-results.tar.gz`; a retry has its own attempt suffix. The bundle folder must contain `preflight.json`, native BFCL raw generation/evaluation outputs under `official_raw/`, command records, `summary.json`, `manifest.json`, `bundle_manifest.json`, and `archive_contents.json`. A blocked/failed attempt is archived for diagnosis but does not produce a score. Run the BFCL-specific verifier only for a summary marked `PASS`; the general integrity verifier runs on every retained attempt.

Download `aether-bfcl-official-results.tar.gz` from the notebook **Output** panel (Kaggle) or JupyterLab file browser (Pod). On Windows, extract it to `C:\AETHER\bfcl-bundle` (create the folder first), then in PowerShell in your clean AETHER clone run:

```powershell
python -m scripts.verify_bfcl_bundle C:\AETHER\bfcl-bundle
python -m scripts.verify_external_bundle C:\AETHER\bfcl-bundle --expected-kind bfcl_official
python -m scripts.ingest_external_bundle C:\AETHER\bfcl-bundle results\phase1\bfcl\official --expected-kind bfcl_official
```

Both verifiers must pass before ingestion. Ingestion refuses to overwrite an
existing destination. Keep the original archive and printed SHA-256. Do not
hand-edit `summary.json` or raw official files.

## Part B ? Agent C locally on Windows (CPU)

**Scope clarification:** this approved protocol is not a new Qwen inference by Agent C. It applies frozen deterministic Agent C to retained real-Qwen A/B traces. A Qwen-powered Agent C would be a different experiment and requires a separate prospective protocol and human approval.

No Kaggle, NVIDIA GPU, CUDA, Transformers, model download or internet is needed
for this approved review. The run uses the small retained qualification rows and
registry from the repo. The test and validation portions of the registry (8
cases each) are not eligible; the runner only accepts declared development
rows. The local computer's 16 GiB RAM and integrated graphics do not constrain
this deterministic review.

### B1. After human approval, create a clean execution clone

Use **PowerShell**. This separate clone keeps your existing uncommitted files
untouched and provides the clean Git commit required for provenance. Run after
the approved decision has been committed/pushed:

```powershell
$runDir = Join-Path $env:USERPROFILE 'aether-agentc-run'
if (Test-Path $runDir) { throw "Choose a new empty path; this guide will not delete or overwrite $runDir" }
git clone --branch m1/target-harness --single-branch https://github.com/ama1a005/aether.git $runDir
Set-Location $runDir
git status --short
py -3.11 --version
$venvDir = Join-Path $env:LOCALAPPDATA 'aether-agentc-venv'
if (-not (Test-Path $venvDir)) { py -3.11 -m venv $venvDir }
$python = Join-Path $venvDir 'Scripts\python.exe'
& $python -m pip install --upgrade pip
& $python -m pip install PyYAML==6.0.3
```

`git status --short` should print nothing. The Python virtual environment is in
`%LOCALAPPDATA%`, outside the clone, so it does not make the evidence source dirty.
Keep the approval JSON in this clean clone at `results\phase1\protocol_approvals\agent_c_qwen_development.json`;
it was included in the approved/pushed commit. The input files already exist in
the clone. No separate data/model upload is required.

If the reviewer has not approved the protocol, **stop here**. Do not use the
unit tests or fixture rows to stand in for the experiment.

### B2. Start the real retained-trace review

First verify the code/config and input paths exist without opening the model
(the runner never loads one):

```powershell
Test-Path results\phase1\protocol_approvals\agent_c_qwen_development.json
Test-Path results\phase1\model_qualification\qwen15b_kaggle_20261110\mq_g1_rows.json
Test-Path data\causal_v2\case_registry.json
& $python -m experiments.phase1.qwen_agent_c --help
```

Then run once, writing results **outside the Git clone**:

```powershell
$output = Join-Path $env:USERPROFILE 'aether-agentc-results'
& $python -m experiments.phase1.qwen_agent_c `
  --config configs\experiments\agent_c_qwen_development.yaml `
  --approval results\phase1\protocol_approvals\agent_c_qwen_development.json `
  --output $output
```

The runner should finish quickly because it evaluates only 48 deterministic
case-condition reviews, not Qwen inference. It prints the path to `raw_reviews.json`.
This is an experiment only after the human approval gate passes; do not run it
before approval. The result must say `SUPPORTING_EVIDENCE_ONLY`, retain invalid
rows in counts, and report zero validation/test executions. It does not qualify
Agent C as a real Qwen model or causal-core result.

If the process is interrupted after the output directory was created, rerun the
same command with `--resume` appended. The runner checks the exact config/input
hash plan and resumes missing case-condition rows; it rejects mismatched or
repeated checkpoint keys. Do not delete or edit the partial `raw_reviews.json`.

### B3. Verify and retain Agent C evidence

Run independent checks before sharing or ingesting anything:

```powershell
& $python -m scripts.verify_agent_c_bundle $output
& $python -m scripts.verify_external_bundle $output --expected-kind qwen_agent_c
```

Both must pass. The bundle includes raw paired reviews, summary, complete hash
inventory, source-Qwen generation provenance, retained prompt/token-id inputs,
per-condition latency/tool calls/errors, and zero protected-split counts. Preserve
the whole output directory. If transferring to another computer, zip it without
changing its contents, then rerun both verifiers after extraction. Ingest only
after verification and only into a new evidence destination:

```powershell
& $python -m scripts.ingest_external_bundle $output `
  results\phase1\agent_c\development --expected-kind qwen_agent_c
```

If that destination already exists, choose the registered new destination only
after checking the repository's evidence registry; do not overwrite.

## Update the final handoff after verification

Do not say a run passed until the independent verifier passes. Record in
`docs/handoffs/target/FINAL_SPRINT_HANDOFF.md` for each experiment:

- approval reviewer and approved proposal/config SHA-256;
- exact source commit, run ID, UTC time, hardware, and command;
- archive/output SHA-256 and verification output;
- actual summary status and eligible/invalid/error denominators;
- validation/test counts (must both be zero);
- remaining failures/limitations and the claim boundary.

Never copy metrics into the handoff unless they are read from the verified raw
bundle. Commit/push only the approved decision/result/handoff files that the
project evidence policy permits. The runbooks and final handoff are linked from
[the Member 1 sprint handoff](FINAL_SPRINT_HANDOFF.md).
