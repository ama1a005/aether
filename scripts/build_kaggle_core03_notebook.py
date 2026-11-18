"""Build the commit-pinned, restart-safe CORE-03 Kaggle notebook."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMMIT = "cbc2844ba84c989ea286721fa1d2ca310cd92634"


def _cell(kind: str, source: str) -> dict[str, object]:
    row: dict[str, object] = {"cell_type": kind,
        "id": hashlib.sha256(source.encode()).hexdigest()[:8], "metadata": {},
        "source": source.splitlines(keepends=True)}
    if kind == "code":
        row.update({"execution_count": None, "outputs": []})
    return row


def build() -> dict[str, object]:
    """Return the complete seven-cell CORE-03 notebook."""
    cells = [
        _cell("markdown", """# AETHER CORE-03 causal remediation comparison

This notebook executes the exact approved CPU-float32 CORE-03 protocol. GPU is
deliberately unused because changing precision/device would change the approved
method. The campaign is only 624 forwards. Every completed arm/seed unit is
uploaded synchronously to a private Hugging Face dataset, so a restarted Kaggle
session resumes at the next incomplete unit.

Kaggle requirements: Internet enabled, standard CPU runtime, and secrets
`HF_TOKEN` plus `AETHER_HF_REPO`. The dataset repository must already exist,
belong to the token owner, and be private.
"""),
        _cell("code", f"""from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,tarfile
WORK=Path('/kaggle/working'); RUNTIME=Path('/tmp/aether-core03'); REPO=RUNTIME/'aether'
VENV=RUNTIME/'venv'; PY=VENV/'bin'/'python'; CACHE=RUNTIME/'hf-cache'
OUTPUT=WORK/'aether-core03-results'; COMMIT={COMMIT!r}; URL='https://github.com/ama1a005/aether.git'
os.environ.update({{'MPLBACKEND':'Agg','PYTHONNOUSERSITE':'1','TOKENIZERS_PARALLELISM':'false',
 'OMP_NUM_THREADS':'4','MKL_NUM_THREADS':'4','OPENBLAS_NUM_THREADS':'4'}})
for path in (RUNTIME,CACHE): path.mkdir(parents=True,exist_ok=True)
print('Host Python:',sys.version); print('Frozen execution: CPU float32; maximum 624 forwards')
"""),
        _cell("code", """# Install isolated Python 3.11 and immutable source.
if shutil.which('uv') is None: subprocess.run([sys.executable,'-m','pip','install','uv'],check=True)
UV=shutil.which('uv'); env=os.environ.copy(); env['UV_PYTHON_INSTALL_DIR']=str(RUNTIME/'uv-python')
if not PY.exists(): subprocess.run([UV,'venv','--python','3.11.9',str(VENV)],check=True,env=env)
if not REPO.exists(): subprocess.run(['git','clone','--branch','lm','--single-branch',URL,str(REPO)],check=True)
subprocess.run(['git','fetch','--no-tags','origin','lm'],cwd=REPO,check=True)
subprocess.run(['git','checkout','--detach',COMMIT],cwd=REPO,check=True)
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()==COMMIT
assert not subprocess.check_output(['git','status','--porcelain'],cwd=REPO,text=True).strip()
lock=WORK/'core03-lock.txt'; lines=(REPO/'requirements-lock.txt').read_text().splitlines()
lock.write_text(chr(10).join(x for x in lines if not x.startswith('torch=='))+chr(10))
subprocess.run([UV,'pip','install','--python',str(PY),'torch==2.14.1','--index-url','https://download.pytorch.org/whl/cpu'],check=True,env=env)
subprocess.run([UV,'pip','install','--python',str(PY),'-r',str(lock)],check=True,env=env)
subprocess.run([UV,'pip','install','--python',str(PY),'--no-deps','-e',str(REPO)],check=True,env=env)
subprocess.run([str(PY),'-m','pytest','tests/unit/test_core03_remediation_freeze.py','tests/unit/test_core03_execution_package.py','tests/unit/test_model_adapter.py','-q'],cwd=REPO,check=True)
"""),
        _cell("code", """# Connect private durable checkpoint storage and restore if present.
from kaggle_secrets import UserSecretsClient
from huggingface_hub import HfApi,hf_hub_download
from huggingface_hub.errors import EntryNotFoundError
secrets=UserSecretsClient(); os.environ['HF_TOKEN']=secrets.get_secret('HF_TOKEN')
HF_REPO=secrets.get_secret('AETHER_HF_REPO'); assert os.environ['HF_TOKEN'] and HF_REPO
api=HfApi(token=os.environ['HF_TOKEN']); info=api.repo_info(repo_id=HF_REPO,repo_type='dataset')
assert info.private, 'AETHER_HF_REPO must already exist and be private'
REMOTE='core03/checkpoint.tar.gz'
try: checkpoint=Path(hf_hub_download(HF_REPO,REMOTE,repo_type='dataset',cache_dir=RUNTIME/'checkpoint-cache'))
except EntryNotFoundError: checkpoint=None
if checkpoint:
 with tarfile.open(checkpoint,'r:gz') as bundle:
  members=bundle.getmembers(); roots={{Path(m.name).parts[0] for m in members if Path(m.name).parts}}
  assert roots=={{'aether-core03-results'}}
  for member in members:
   if Path(member.name).is_absolute() or '..' in Path(member.name).parts or member.issym() or member.islnk(): raise ValueError(member.name)
  bundle.extractall(WORK,filter='data')
 print('Restored checkpoint:',checkpoint)
else: print('No remote checkpoint; starting a fresh CORE-03 campaign')
"""),
        _cell("code", """# Download/reuse the immutable model snapshot with one worker.
revision='989aa7980e4cf806f80c7fef2b1adb7bc71aa306'
code="from huggingface_hub import snapshot_download; print(snapshot_download('Qwen/Qwen2.5-1.5B-Instruct',revision='"+revision+"',cache_dir=r'"+str(CACHE)+"',max_workers=1))"
snapshot=Path(subprocess.check_output([str(PY),'-c',code],text=True).strip())
assert snapshot.name==revision; print('Snapshot ready:',snapshot)
"""),
        _cell("code", """# Run the pre-access gate once, or validate the restored gate.
if not OUTPUT.exists():
 subprocess.run([str(PY),'-m','experiments.phase1.core03_remediation','--preflight-only',
                 '--output',str(OUTPUT),'--model-snapshot',str(snapshot)],cwd=REPO,check=True)
else:
 gate=json.loads((OUTPUT/'preflight.json').read_text())
 assert gate['overall']=='PASS' and gate['model_accessed'] is False
 print('Restored passing preflight at commit',gate['git_commit'])
"""),
        _cell("code", """# Resume execution. Output is streamed; each of 15 units is remotely committed.
command=[str(PY),'-u','-m','experiments.phase1.core03_remediation','--resume',
         '--output',str(OUTPUT),'--model-snapshot',str(snapshot),
         '--checkpoint-repo',HF_REPO,'--checkpoint-path','core03/checkpoint.tar.gz']
process=subprocess.Popen(command,cwd=REPO,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
assert process.stdout is not None
for line in process.stdout: print(line,end='',flush=True)
code=process.wait()
if code: raise subprocess.CalledProcessError(code,command)
"""),
        _cell("code", """# Independently verify, export, and remotely retain the final archive.
subprocess.run([str(PY),'-m','scripts.verify_core03_remediation_bundle',str(OUTPUT)],cwd=REPO,check=True)
archive=WORK/'aether-core03-results.tar.gz'
with tarfile.open(archive,'w:gz') as bundle: bundle.add(OUTPUT,arcname=OUTPUT.name)
digest=hashlib.sha256(archive.read_bytes()).hexdigest(); print('FINAL ARCHIVE',archive); print('SHA256',digest)
api.upload_file(path_or_fileobj=archive,path_in_repo='core03/final-results.tar.gz',repo_id=HF_REPO,
                repo_type='dataset',commit_message='verified CORE-03 final result')
print('Final archive retained at',HF_REPO,'core03/final-results.tar.gz')
"""),
    ]
    return {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3",
        "language": "python", "name": "python3"}}, "nbformat": 4, "nbformat_minor": 5}


def main() -> None:
    output = ROOT / "notebooks/aether_qwen_core03_remediation.ipynb"
    output.write_text(json.dumps(build(), indent=1) + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
