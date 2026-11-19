"""Build the commit-pinned, checkpoint-safe real-Qwen Agent C notebook."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re


def _cell(kind: str, source: str) -> dict[str, object]:
    row: dict[str, object] = {"cell_type": kind, "id": hashlib.sha256(source.encode()).hexdigest()[:8],
                              "metadata": {}, "source": source.splitlines(keepends=True)}
    if kind == "code": row.update({"execution_count": None, "outputs": []})
    return row


def build(commit: str) -> dict[str, object]:
    """Return a clean notebook bound to one immutable source commit."""
    if re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        raise ValueError("real-Qwen Agent C notebook requires a 40-hex commit")
    setup = f"""from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,tarfile
from kaggle_secrets import UserSecretsClient
WORK=Path('/kaggle/working'); RUNTIME=Path('/tmp/aether-agent-c-real')
REPO=RUNTIME/'aether'; VENV=RUNTIME/'venv'; PY=VENV/'bin'/'python'
OUTPUT=WORK/'aether-qwen-agent-c-real'; CACHE=RUNTIME/'hf-cache'
COMMIT={commit!r}; URL='https://github.com/ama1a005/aether.git'
REMOTE_PATH='agent-c-real/checkpoint_state.json'
os.environ.update({{'PYTHONNOUSERSITE':'1','MPLBACKEND':'Agg'}})
RUNTIME.mkdir(parents=True,exist_ok=True)
secrets=UserSecretsClient(); os.environ['HF_TOKEN']=secrets.get_secret('HF_TOKEN')
HF_REPO=secrets.get_secret('AETHER_HF_REPO')
assert os.environ['HF_TOKEN'] and HF_REPO and '/' in HF_REPO, 'Enable HF_TOKEN and AETHER_HF_REPO secrets for this notebook'
"""
    environment = """if shutil.which('uv') is None: subprocess.run([sys.executable,'-m','pip','install','uv==0.11.8'],check=True)
UV=shutil.which('uv'); env=os.environ.copy(); env['UV_PYTHON_INSTALL_DIR']=str(RUNTIME/'uv-python')
if not PY.is_file():
 subprocess.run([UV,'venv','--python','3.11.9',str(VENV)],check=True,env=env)
subprocess.run([str(PY),'-c','import sys; assert sys.version_info[:3]==(3,11,9),sys.version'],check=True)
if not REPO.exists():
 subprocess.run(['git','clone','--branch','lm','--single-branch',URL,str(REPO)],check=True)
elif not (REPO/'.git').exists():
 raise RuntimeError(f'Existing repository path is incomplete: {REPO}')
subprocess.run(['git','fetch','origin',COMMIT],cwd=REPO,check=True)
subprocess.run(['git','checkout','--detach',COMMIT],cwd=REPO,check=True)
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()==COMMIT
lines=(REPO/'requirements-lock.txt').read_text().splitlines(); lock=RUNTIME/'lock.txt'
lock.write_text(chr(10).join(x for x in lines if not x.startswith('torch=='))+chr(10),encoding='utf-8')
subprocess.run([UV,'pip','install','--python',str(PY),'torch==2.14.1','--index-url','https://download.pytorch.org/whl/cu130'],check=True,env=env)
subprocess.run([UV,'pip','install','--python',str(PY),'-r',str(lock)],check=True,env=env)
subprocess.run([UV,'pip','install','--python',str(PY),'--no-deps','-e',str(REPO)],check=True,env=env)
subprocess.run([str(PY),'-m','pytest','tests/unit/test_qwen_agent_c_real.py','tests/unit/test_qwen_agent_c_real_proposal.py','-q'],cwd=REPO,check=True)
"""
    remote = """from huggingface_hub import HfApi,hf_hub_download
from huggingface_hub.errors import EntryNotFoundError
api=HfApi(token=os.environ['HF_TOKEN']); info=api.repo_info(HF_REPO,repo_type='dataset')
assert info.private, 'AETHER_HF_REPO must name an existing private dataset repository'
try:
    remote_checkpoint=Path(hf_hub_download(HF_REPO,REMOTE_PATH,repo_type='dataset',cache_dir=RUNTIME/'checkpoint-cache',force_download=True))
except EntryNotFoundError:
    remote_checkpoint=None
if remote_checkpoint is not None:
    OUTPUT.mkdir(parents=True,exist_ok=True)
    shutil.copy2(remote_checkpoint,OUTPUT/'checkpoint_state.json')
print('Resume rows:',len(json.loads((OUTPUT/'checkpoint_state.json').read_text())['rows']) if remote_checkpoint else 0)
"""
    snapshot = """import torch
assert torch.cuda.is_available(), 'Enable a Kaggle GPU accelerator'
from huggingface_hub import snapshot_download
REVISION='989aa7980e4cf806f80c7fef2b1adb7bc71aa306'
snapshot=Path(snapshot_download('Qwen/Qwen2.5-1.5B-Instruct',revision=REVISION,cache_dir=CACHE,max_workers=2))
frozen_path=REPO/'results/phase1/model_qualification/qwen15b_kaggle_20261110/model_snapshot_manifest.json'
frozen=json.loads(frozen_path.read_text(encoding='utf-8'))
expected={x['path']:(x['size'],x['sha256']) for x in frozen['files']}
observed={p.relative_to(snapshot).as_posix():(p.stat().st_size,hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(snapshot.rglob('*')) if p.is_file()}
assert observed==expected, 'Model snapshot differs from qualified Qwen revision'
manifest=WORK/'agent-c-model-snapshot.json'
manifest.write_text(json.dumps({'model_id':'Qwen/Qwen2.5-1.5B-Instruct','resolved_revision':REVISION,'files':[{'path':k,'size':v[0],'sha256':v[1]} for k,v in observed.items()]},indent=2),encoding='utf-8')
"""
    execute = """command=[str(PY),'-u','-m','experiments.phase1.qwen_agent_c_real','--output',str(OUTPUT),
         '--model-snapshot',str(snapshot),'--snapshot-manifest',str(manifest),
         '--checkpoint-repo',HF_REPO,'--checkpoint-path',REMOTE_PATH]
if (OUTPUT/'checkpoint_state.json').is_file(): command.append('--resume')
subprocess.run(command,cwd=REPO,env=os.environ,check=True)
subprocess.run([str(PY),'-m','scripts.verify_qwen_agent_c_real_bundle',str(OUTPUT)],cwd=REPO,env=os.environ,check=True)
archive=WORK/'aether-qwen-agent-c-real-results.tar.gz'
with tarfile.open(archive,'w:gz') as bundle: bundle.add(OUTPUT,arcname=OUTPUT.name)
api.upload_file(path_or_fileobj=archive,path_in_repo='agent-c-real/final-results.tar.gz',repo_id=HF_REPO,repo_type='dataset',commit_message='Verified real-Qwen Agent C final bundle')
print('Archive:',archive,'SHA-256:',hashlib.sha256(archive.read_bytes()).hexdigest())
"""
    cells = [_cell("markdown", "# AETHER real-Qwen Agent C v1\n\nRun all cells with one T4 or better GPU. Secrets: `HF_TOKEN`, `AETHER_HF_REPO` (an existing private Hugging Face dataset). Progress is uploaded after every case-condition."),
             _cell("code", setup), _cell("code", environment), _cell("code", remote),
             _cell("code", snapshot), _cell("code", execute)]
    return {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}}, "nbformat": 4, "nbformat_minor": 5}


def main() -> None:
    """Write the notebook."""
    parser = argparse.ArgumentParser(); parser.add_argument("--commit", required=True)
    parser.add_argument("--output", type=Path, required=True); args = parser.parse_args()
    args.output.write_text(json.dumps(build(args.commit), indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
