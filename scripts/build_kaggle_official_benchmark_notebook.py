"""Build a commit-pinned Kaggle notebook for BFCL or AgentDojo native execution."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]

UV_VERSION_PARSER = """def parse_uv_version(output):
    match=re.match(r'^\\s*uv\\s+(\\d+\\.\\d+\\.\\d+)(?:\\s|$)',output)
    if match is None:
        raise RuntimeError(f'Could not parse uv version from --version output: {output!r}')
    return match.group(1)
"""


def _cell(kind: str, source: str) -> dict[str, object]:
    row: dict[str, object] = {"cell_type": kind, "id": hashlib.sha256(source.encode()).hexdigest()[:8],
                              "metadata": {}, "source": source.splitlines(keepends=True)}
    if kind == "code":
        row.update({"execution_count": None, "outputs": []})
    return row


def build(benchmark: str, commit: str) -> dict[str, object]:
    """Return a clean notebook pinned to one source commit and benchmark."""
    if benchmark not in {"bfcl", "agentdojo"}:
        raise ValueError("benchmark must be bfcl or agentdojo")
    if re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        raise ValueError("notebook requires an immutable 40-hex source commit")
    if benchmark == "bfcl":
        package_setup = """import hashlib
WHEELHOUSE=RUNTIME/'wheelhouse'; WHEELHOUSE.mkdir(parents=True,exist_ok=True)
subprocess.run([str(PY),'-m','pip','download','--no-deps','--only-binary=:all:','--dest',str(WHEELHOUSE),'bfcl_eval==2026.3.23'],check=True)
WHEELS=sorted(WHEELHOUSE.glob('bfcl_eval-2026.3.23-*.whl'))
assert len(WHEELS)==1, f'Expected exactly one pinned BFCL wheel, found {len(WHEELS)}'
WHEEL=WHEELS[0]; WHEEL_SHA256=hashlib.sha256(WHEEL.read_bytes()).hexdigest()
assert WHEEL_SHA256=='3bb6dfa5f0c68ad403c9ec50b00db2bb3b4cc9b38ab1ff33f48fe30d853d3a0a', WHEEL_SHA256
subprocess.run([str(PY),'-m','pip','install',str(WHEEL)],check=True)
subprocess.run([UV,'pip','install','--python',str(PY),'-r',str(REPO/'requirements-bfcl-vllm.txt'),'--torch-backend','cu130'],check=True,env=env)
assert subprocess.check_output([str(PY),'-c','import torch; from importlib.metadata import version; print(version("vllm"),torch.__version__,torch.version.cuda)'],text=True).strip().startswith('0.34.0 2.14.0+ 13.0')
"""
        snapshot_setup = """if not globals().get('SETUP_COMPLETE',False):
    raise RuntimeError('Repository setup is incomplete. Run all preceding setup cells successfully in order.')
if not globals().get('DEPENDENCIES_COMPLETE',False):
    raise RuntimeError('Dependency installation or model-free tests did not complete. Fix the preceding cell before continuing.')
if not REPO.is_dir() or not PY.is_file() or 'env' not in globals():
    raise RuntimeError('Repository, pinned Python, or environment is missing. Restart with a fresh Kaggle session and run cells in order.')
import sys
sys.path.insert(0,str(REPO))
if Path.cwd()!=REPO:
    os.chdir(REPO)
actual_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()
if actual_commit!=COMMIT:
    raise RuntimeError(f'Expected pinned repository commit {COMMIT}, found {actual_commit}')
from huggingface_hub import snapshot_download
from benchmarks.run_native_official import _load_config
from benchmarks.nov19_bfcl.preflight import check_backend_and_hardware, check_package
from causal.remediation_freeze import frozen_text_hash_matches
from experiments.external_bundle import verify_protocol_approval
CONFIG=REPO/'configs/benchmarks/phase1_external.yaml'
_load_config(CONFIG,'bfcl')
APPROVAL=REPO/'results/phase1/protocol_approvals/bfcl_official.json'
verify_protocol_approval(CONFIG,APPROVAL)
wheel_ok,wheel_reasons,_=check_package(wheel_path=WHEEL)
gpu_ok,gpu_reasons,gpu_details=check_backend_and_hardware('vllm',1)
assert wheel_ok, wheel_reasons
assert gpu_ok, {'reasons':gpu_reasons,'details':gpu_details}
FROZEN_MANIFEST=REPO/'results/phase1/model_qualification/qwen15b_kaggle_20261110/model_snapshot_manifest.json'
assert frozen_text_hash_matches(FROZEN_MANIFEST,'1b282b730f38fbe992608e8837fe0f619463a767f93e08d97cd0950d55644f11')
frozen=json.loads(FROZEN_MANIFEST.read_text(encoding='utf-8'))
REVISION='989aa7980e4cf806f80c7fef2b1adb7bc71aa306'
snapshot=Path(snapshot_download('Qwen/Qwen2.5-1.5B-Instruct',revision=REVISION,cache_dir=RUNTIME/'hf-cache',max_workers=1))
expected={item['path']:(item['size'],item['sha256']) for item in frozen['files']}
observed={p.relative_to(snapshot).as_posix():(p.stat().st_size,hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(snapshot.rglob('*')) if p.is_file()}
assert observed==expected, 'Downloaded snapshot differs from the independently retained qualification manifest'
SNAPSHOT_MANIFEST=WORK/'model_snapshot_manifest.json'
SNAPSHOT_MANIFEST.write_text(json.dumps({'model_id':'Qwen/Qwen2.5-1.5B-Instruct','resolved_revision':REVISION,'tokenizer_revision':REVISION,'snapshot_path':str(snapshot),'files':[{'path':name,'size':size,'sha256':digest} for name,(size,digest) in sorted(observed.items())]},indent=2),encoding='utf-8')
PREFLIGHT_COMPLETE=True
"""
        benchmark_verification = """bfcl_summary=json.loads((OUTPUT/'summary.json').read_text(encoding='utf-8'))
if bfcl_summary.get('overall')=='PASS':
    subprocess.run([str(PY),'-m','scripts.verify_bfcl_bundle',str(OUTPUT)],cwd=REPO,check=True)
else:
    print('Retaining a blocked/failed BFCL attempt; this is not a score.')
"""
    else:
        package_setup = "subprocess.run([UV,'pip','install','--python',str(PY),'agentdojo==0.1.35'],check=True,env=env)\n"
        snapshot_setup = ""
        benchmark_verification = ""
    cells = [
        _cell("markdown", f"""# AETHER {benchmark.upper()} official execution

Runs the pinned native official package on development-scoped preparation only.
This notebook does not access AETHER validation/test splits. It exports raw
official outputs plus a hash-verified AETHER wrapper bundle.
"""),
        _cell("code", f"""from pathlib import Path
import json,os,re,shutil,subprocess,sys,tarfile,hashlib,threading,time
from kaggle_secrets import UserSecretsClient
WORK=Path('/kaggle/working') if Path('/kaggle/working').is_dir() else Path.cwd()/'aether-execution-output'
WORK.mkdir(parents=True,exist_ok=True)
ATTEMPT=os.environ.get('AETHER_BFCL_ATTEMPT','attempt-1')
assert re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{{0,63}}',ATTEMPT), f'Invalid attempt identifier: {{ATTEMPT!r}}'
RUNTIME=Path('/tmp/aether-{benchmark}')
REPO=RUNTIME/'aether'; VENV=RUNTIME/'venv'; PY=VENV/'bin'/'python'
OUTPUT=WORK/f'aether-{benchmark}-official-{{ATTEMPT}}'; COMMIT={commit!r}
if OUTPUT.exists(): raise FileExistsError(f'Refusing to repeat or overwrite this attempt: {{OUTPUT}}')
URL='https://github.com/ama1a005/aether.git'
os.environ.update({{'PYTHONNOUSERSITE':'1','MPLBACKEND':'Agg'}})
RUNTIME.mkdir(parents=True,exist_ok=True)
secrets=UserSecretsClient(); os.environ['HF_TOKEN']=secrets.get_secret('HF_TOKEN')
HF_REPO=secrets.get_secret('AETHER_HF_REPO')
assert os.environ['HF_TOKEN'] and HF_REPO and '/' in HF_REPO, 'Enable HF_TOKEN and AETHER_HF_REPO secrets'
"""),
        _cell("code", f"""if 'RUNTIME' not in globals() or 'REPO' not in globals() or 'VENV' not in globals():
    raise RuntimeError('Setup variables are missing. Run the notebook setup cell (Cell 1) successfully before this cell.')
if RUNTIME.exists() and (REPO.exists() or VENV.exists()):
    raise RuntimeError(f'Execution paths already exist under {{RUNTIME}}. Use a fresh Kaggle session; existing files are preserved.')
subprocess.run([sys.executable,'-m','pip','install','--upgrade','uv==0.11.8'],check=True)
UV=shutil.which('uv')
if UV is None:
    raise RuntimeError('Pinned uv==0.11.8 installation succeeded but no uv executable is on PATH.')
{UV_VERSION_PARSER}
uv_output=subprocess.check_output([UV,'--version'],text=True).strip()
uv_version=parse_uv_version(uv_output)
if uv_version!='0.11.8':
    raise RuntimeError(f'Expected uv 0.11.8; found version {{uv_version!r}} in {{uv_output!r}}')
env=os.environ.copy(); env['UV_PYTHON_INSTALL_DIR']=str(RUNTIME/'uv-python')
subprocess.run([UV,'venv','--python','3.11.9',str(VENV)],check=True,env=env)
if not PY.is_file():
    raise RuntimeError(f'uv did not create the expected Python executable: {{PY}}')
subprocess.run(['git','clone','--branch','lm','--single-branch',URL,str(REPO)],check=True)
subprocess.run(['git','fetch','origin','m1/target-harness'],cwd=REPO,check=True)
subprocess.run(['git','checkout','--detach',COMMIT],cwd=REPO,check=True)
actual_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()
if actual_commit!=COMMIT:
    raise RuntimeError(f'Checked out {{actual_commit}}, expected pinned commit {{COMMIT}}')
if subprocess.check_output(['git','status','--porcelain'],cwd=REPO,text=True).strip():
    raise RuntimeError('Pinned source checkout is not clean; refusing dependency setup.')
SETUP_COMPLETE=True
"""),
        _cell("code", f"""if not globals().get('SETUP_COMPLETE',False):
    raise RuntimeError('Repository setup is incomplete. Run the preceding setup cell successfully before installing dependencies.')
if not REPO.is_dir() or not PY.is_file() or 'env' not in globals():
    raise RuntimeError('Repository, pinned Python, or environment is missing. Restart with a fresh Kaggle session and run cells in order.')
subprocess.run([str(PY),'-m','ensurepip','--upgrade'],check=True)
subprocess.run([str(PY),'-m','pip','--version'],check=True)
subprocess.run([UV,'pip','install','--python',str(PY),'-r',str(REPO/'requirements-lock.txt')],check=True,env=env)
{package_setup}
subprocess.run([str(PY),'-m','pytest','tests/unit/test_external_bundle.py','tests/unit/test_native_benchmark_runners.py','tests/unit/test_native_official_package.py','-q'],cwd=REPO,check=True)
DEPENDENCIES_COMPLETE=True
"""),
        *([_cell("code", snapshot_setup)] if snapshot_setup else []),
        _cell("code", f"""if {"not globals().get('PREFLIGHT_COMPLETE',False)" if benchmark == 'bfcl' else "not globals().get('SETUP_COMPLETE',False)"}:
    raise RuntimeError('Required setup/preflight cells did not complete. Run all preceding cells in order.')
command=[str(PY),'-m','benchmarks.run_native_official',{benchmark!r},'--config',str(REPO/'configs/benchmarks/phase1_external.yaml'),'--output',str(OUTPUT)]
{("command += ['--snapshot-manifest',str(SNAPSHOT_MANIFEST),'--package-wheel',str(WHEEL),'--backend','vllm','--num-gpus','1']" if benchmark == 'bfcl' else "")}
from huggingface_hub import HfApi
api=HfApi(token=os.environ['HF_TOKEN']); info=api.repo_info(HF_REPO,repo_type='dataset')
assert info.private, 'AETHER_HF_REPO must be an existing private dataset repository'
REMOTE_PREFIX=f'{benchmark}-official/{{ATTEMPT}}'
checkpoint_archive=WORK/f'aether-{benchmark}-{{ATTEMPT}}-checkpoint.tar.gz'
sync_stop=threading.Event(); sync_errors=[]
def upload_checkpoint():
 if not OUTPUT.is_dir() or not any(path.is_file() for path in OUTPUT.rglob('*')): return
 temporary=checkpoint_archive.with_suffix('.tmp')
 with tarfile.open(temporary,'w:gz') as bundle: bundle.add(OUTPUT,arcname=OUTPUT.name)
 temporary.replace(checkpoint_archive)
 api.upload_file(path_or_fileobj=str(checkpoint_archive),path_in_repo=f'{{REMOTE_PREFIX}}/checkpoint.tar.gz',repo_id=HF_REPO,repo_type='dataset',commit_message=f'{benchmark.upper()} retained checkpoint')
def sync_loop():
 while not sync_stop.wait(300):
  try: upload_checkpoint()
  except BaseException as error: sync_errors.append(error); print('Remote checkpoint error:',type(error).__name__,str(error),flush=True)
sync_thread=threading.Thread(target=sync_loop,daemon=True); sync_thread.start()
try:
 subprocess.run(command,cwd=REPO,check=True)
finally:
 sync_stop.set(); sync_thread.join(timeout=15)
 upload_checkpoint()
if sync_errors: raise RuntimeError('One or more periodic Hugging Face checkpoint uploads failed') from sync_errors[0]
subprocess.run([str(PY),'-m','scripts.verify_external_bundle',str(OUTPUT),'--expected-kind',{(benchmark + '_official')!r}],cwd=REPO,check=True)
{benchmark_verification}
archive=WORK/f'aether-{benchmark}-official-{{ATTEMPT}}-results.tar.gz'
with tarfile.open(archive,'w:gz') as bundle: bundle.add(OUTPUT,arcname=OUTPUT.name)
api.upload_file(path_or_fileobj=str(archive),path_in_repo=f'{{REMOTE_PREFIX}}/final-results.tar.gz',repo_id=HF_REPO,repo_type='dataset',commit_message=f'Verified {benchmark.upper()} final bundle')
print(archive,hashlib.sha256(archive.read_bytes()).hexdigest())
"""),
    ]
    return {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}}, "nbformat": 4, "nbformat_minor": 5}


def main() -> None:
    """Write a selected official-benchmark notebook."""
    parser = argparse.ArgumentParser()
    parser.add_argument("benchmark", choices=("bfcl", "agentdojo"))
    parser.add_argument("--commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    arguments.output.write_text(json.dumps(build(arguments.benchmark, arguments.commit), indent=1) + "\n", encoding="utf-8")
    print(arguments.output)


if __name__ == "__main__":
    main()
