"""Build the commit-pinned, remotely checkpointed real-Qwen red-team notebook."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re


def _cell(kind: str, source: str) -> dict[str, object]:
    row: dict[str, object] = {
        "cell_type": kind,
        "id": hashlib.sha256(source.encode()).hexdigest()[:8],
        "metadata": {},
        "source": source.splitlines(keepends=True),
    }
    if kind == "code":
        row.update({"execution_count": None, "outputs": []})
    return row


def build(commit: str) -> dict[str, object]:
    """Return a clean notebook pinned to one immutable source commit."""
    if re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        raise ValueError("red-team notebook requires a 40-hex commit")
    setup = f"""from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,tarfile
from kaggle_secrets import UserSecretsClient
WORK=Path('/kaggle/working'); RUNTIME=Path('/tmp/aether-red-team-real')
REPO=RUNTIME/'aether'; VENV=RUNTIME/'venv'; PY=VENV/'bin'/'python'
OUTPUT=WORK/'aether-qwen-red-team-real'; CACHE=RUNTIME/'hf-cache'
COMMIT={commit!r}; URL='https://github.com/ama1a005/aether.git'
REMOTE_CHECKPOINT='red-team-real/checkpoint.tar.gz'
REMOTE_FINAL='red-team-real/final-results.tar.gz'
os.environ.update({{'PYTHONNOUSERSITE':'1','MPLBACKEND':'Agg'}})
RUNTIME.mkdir(parents=True,exist_ok=True)
secrets=UserSecretsClient(); os.environ['HF_TOKEN']=secrets.get_secret('HF_TOKEN')
HF_REPO=secrets.get_secret('AETHER_HF_REPO')
assert os.environ['HF_TOKEN'] and HF_REPO and '/' in HF_REPO, 'Enable HF_TOKEN and AETHER_HF_REPO secrets'
"""
    environment = """if shutil.which('uv') is None:
 subprocess.run([sys.executable,'-m','pip','install','uv==0.11.8'],check=True)
UV=shutil.which('uv'); env=os.environ.copy(); env['UV_PYTHON_INSTALL_DIR']=str(RUNTIME/'uv-python')
if not PY.is_file():
 subprocess.run([UV,'venv','--python','3.11.9',str(VENV)],check=True,env=env)
subprocess.run([str(PY),'-c','import sys; assert sys.version_info[:3]==(3,11,9),sys.version'],check=True)
if not REPO.exists():
 subprocess.run(['git','clone','--branch','lm','--single-branch',URL,str(REPO)],check=True)
elif not (REPO/'.git').exists():
 raise RuntimeError(f'Existing repository path is incomplete: {REPO}')
subprocess.run(['git','fetch','origin','m1/target-harness'],cwd=REPO,check=True)
subprocess.run(['git','checkout','--detach',COMMIT],cwd=REPO,check=True)
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()==COMMIT
assert not subprocess.check_output(['git','status','--porcelain'],cwd=REPO,text=True).strip()
lines=(REPO/'requirements-lock.txt').read_text().splitlines(); lock=RUNTIME/'lock.txt'
lock.write_text(chr(10).join(x for x in lines if not x.startswith('torch=='))+chr(10),encoding='utf-8')
subprocess.run([UV,'pip','install','--python',str(PY),'torch==2.14.1','--index-url','https://download.pytorch.org/whl/cu130'],check=True,env=env)
subprocess.run([UV,'pip','install','--python',str(PY),'-r',str(lock)],check=True,env=env)
subprocess.run([UV,'pip','install','--python',str(PY),'--no-deps','-e',str(REPO)],check=True,env=env)
subprocess.run([str(PY),'-m','pytest','tests/unit/test_qwen_red_team_package.py','tests/unit/test_qwen_red_team_backend.py','tests/unit/test_red_team_orchestration.py','-q'],cwd=REPO,check=True)
"""
    remote = """from huggingface_hub import HfApi,hf_hub_download
from huggingface_hub.errors import EntryNotFoundError
api=HfApi(token=os.environ['HF_TOKEN']); info=api.repo_info(HF_REPO,repo_type='dataset')
assert info.private, 'AETHER_HF_REPO must be an existing private dataset repository'
try:
 retained=Path(hf_hub_download(HF_REPO,REMOTE_CHECKPOINT,repo_type='dataset',cache_dir=RUNTIME/'checkpoint-cache',force_download=True))
except EntryNotFoundError:
 retained=None
if retained is not None:
 with tarfile.open(retained,'r:gz') as bundle:
  members=bundle.getmembers()
  if any(Path(member.name).is_absolute() or '..' in Path(member.name).parts for member in members):
   raise ValueError('unsafe red-team checkpoint archive member')
  bundle.extractall(WORK)
 assert (OUTPUT/'plan.json').is_file(), 'restored red-team checkpoint lacks plan.json'
print('Resume:',retained is not None)
"""
    snapshot = """import torch
assert torch.cuda.is_available(), 'Enable a Kaggle GPU accelerator'
from huggingface_hub import snapshot_download
REVISION='989aa7980e4cf806f80c7fef2b1adb7bc71aa306'
snapshot=Path(snapshot_download('Qwen/Qwen2.5-1.5B-Instruct',revision=REVISION,cache_dir=CACHE,max_workers=2))
frozen=json.loads((REPO/'results/phase1/model_qualification/qwen15b_kaggle_20261110/model_snapshot_manifest.json').read_text(encoding='utf-8'))
expected={x['path']:(x['size'],x['sha256']) for x in frozen['files']}
observed={p.relative_to(snapshot).as_posix():(p.stat().st_size,hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(snapshot.rglob('*')) if p.is_file()}
assert observed==expected, 'Model snapshot differs from qualified Qwen revision'
manifest=WORK/'red-team-model-snapshot.json'
manifest.write_text(json.dumps({'model_id':'Qwen/Qwen2.5-1.5B-Instruct','resolved_revision':REVISION,'snapshot_path':str(snapshot),'files':[{'path':k,'size':v[0],'sha256':v[1]} for k,v in observed.items()]},indent=2),encoding='utf-8')
"""
    execute = """command=[str(PY),'-u','-m','experiments.phase1.qwen_red_team',
 '--config',str(REPO/'configs/experiments/qwen_red_team_development.yaml'),
 '--approval',str(REPO/'results/phase1/protocol_approvals/qwen_red_team_development.json'),
 '--snapshot-manifest',str(manifest),'--output',str(OUTPUT),
 '--checkpoint-repo',HF_REPO,'--checkpoint-path',REMOTE_CHECKPOINT]
if (OUTPUT/'plan.json').is_file(): command.append('--resume')
subprocess.run(command,cwd=REPO,env=os.environ,check=True)
subprocess.run([str(PY),'-m','scripts.verify_external_bundle',str(OUTPUT),'--expected-kind','qwen_red_team'],cwd=REPO,check=True)
archive=WORK/'aether-qwen-red-team-real-results.tar.gz'
with tarfile.open(archive,'w:gz') as bundle: bundle.add(OUTPUT,arcname=OUTPUT.name)
api.upload_file(path_or_fileobj=str(archive),path_in_repo=REMOTE_FINAL,repo_id=HF_REPO,repo_type='dataset',commit_message='Verified real-Qwen red-team final bundle')
print('Archive:',archive,'SHA-256:',hashlib.sha256(archive.read_bytes()).hexdigest())
"""
    cells = [
        _cell("markdown", "# AETHER real-Qwen red-team\n\nRun all cells on one T4 or better GPU. Every completed attack attempt is saved to the configured private Hugging Face dataset."),
        _cell("code", setup),
        _cell("code", environment),
        _cell("code", remote),
        _cell("code", snapshot),
        _cell("code", execute),
    ]
    return {
        "cells": cells,
        "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}},
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def main() -> None:
    """Write the notebook."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(build(args.commit), indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
