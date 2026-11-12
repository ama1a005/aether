"""Build the uploadable Kaggle notebook for prospective QCI-2 discovery."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_URL = "https://github.com/ama1a005/aether.git"
REPOSITORY_COMMIT = "f26a3f0c932c652cc86d628fe6ac18bc9b08391a"
MODEL_ID = "Qwen/Qwen2.5-1.5B-Instruct"
MODEL_REVISION = "989aa7980e4cf806f80c7fef2b1adb7bc71aa306"
OUTPUT = ROOT / "notebooks/aether_qwen_qci2_semantic_cpu.ipynb"


def _cell(kind: str, source: str) -> dict[str, object]:
    """Create one deterministic notebook cell without stored output."""
    cell: dict[str, object] = {
        "cell_type": kind,
        "id": hashlib.sha256((kind + source).encode()).hexdigest()[:8],
        "metadata": {}, "source": source.splitlines(keepends=True),
    }
    if kind == "code":
        cell.update({"execution_count": None, "outputs": []})
    return cell


def build() -> dict[str, object]:
    """Return the immutable one-attempt CPU QCI-2 discovery notebook."""
    cells = [
        _cell("markdown", """# AETHER Qwen2.5-1.5B QCI-2 semantic controls

Runs the prospectively frozen QCI-2 development-discovery campaign. QCI-1's
negative result remains unchanged. QCI-2 distinguishes same-decision semantic
generalization from opposite-decision specificity, reusing all 12 candidates
without reselection. Audit, validation and test remain closed.

Run all cells once with Internet enabled. Use a Kaggle CPU session with at least
12 GiB available RAM; GPUs are intentionally unused to preserve the qualified
CPU-float32 condition. Preserve and download the archive even if execution fails.
"""),
        _cell("code", f"""from pathlib import Path
import hashlib,json,os,platform,shutil,subprocess,sys,tarfile,time
WORK=Path('/kaggle/working'); RUNTIME=Path('/tmp/aether-qci2-discovery')
REPO,VENV=RUNTIME/'aether',RUNTIME/'venv'; PY=VENV/'bin'/'python'
HF_CACHE=RUNTIME/'hf-cache'; OUTPUT=WORK/'aether-qci2-discovery'
for path in (RUNTIME,HF_CACHE,OUTPUT): path.mkdir(parents=True,exist_ok=True)
REPOSITORY_URL={REPOSITORY_URL!r}; REPOSITORY_COMMIT={REPOSITORY_COMMIT!r}
MODEL_ID={MODEL_ID!r}; MODEL_REVISION={MODEL_REVISION!r}
assert len(REPOSITORY_COMMIT)==40 and all(c in '0123456789abcdef' for c in REPOSITORY_COMMIT)
os.environ.update({{'MPLBACKEND':'Agg','PYTHONNOUSERSITE':'1','TOKENIZERS_PARALLELISM':'false',
                   'OMP_NUM_THREADS':'2','MKL_NUM_THREADS':'2','OPENBLAS_NUM_THREADS':'2'}})
for name in ('AETHER_RUN_REAL_MODEL_TESTS','AETHER_RUN_CALIBRATION_MODELS','AETHER_RUN_DEMO_E2E'):
    os.environ.pop(name,None)
def run_logged(name,command,cwd=None,timeout=3600,check=True):
    path=OUTPUT/(name+'.log')
    with path.open('w',encoding='utf-8') as log:
        process=subprocess.Popen(command,cwd=cwd,env=os.environ.copy(),stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT,text=True,bufsize=1)
        try:
            assert process.stdout is not None; started=time.monotonic()
            for line in process.stdout:
                print(line,end='',flush=True); log.write(line); log.flush()
                if time.monotonic()-started>timeout: raise subprocess.TimeoutExpired(command,timeout)
            code=process.wait()
        except BaseException:
            process.terminate()
            try: process.wait(timeout=30)
            except subprocess.TimeoutExpired: process.kill(); process.wait()
            raise
    if check and code: raise subprocess.CalledProcessError(code,command)
    return code
print('Kaggle Python:',sys.version); print('Platform:',platform.platform())
"""),
        _cell("code", """# Install isolated CPython 3.11.9 and check out the immutable QCI-2 source.
if shutil.which('uv') is None: subprocess.run([sys.executable,'-m','pip','install','uv'],check=True)
UV=shutil.which('uv'); assert UV
uv_env=os.environ.copy(); uv_env['UV_PYTHON_INSTALL_DIR']=str(RUNTIME/'uv-python'); uv_env['UV_CACHE_DIR']=str(RUNTIME/'uv-cache')
if not PY.exists(): subprocess.run([UV,'venv','--python','3.11.9',str(VENV)],check=True,env=uv_env)
subprocess.run([str(PY),'-c','import sys; assert sys.version_info[:3]==(3,11,9); print(sys.executable,sys.version)'],check=True)
if not REPO.exists(): subprocess.run(['git','clone','--branch','lm','--single-branch',REPOSITORY_URL,str(REPO)],check=True)
subprocess.run(['git','fetch','--no-tags','origin','lm'],cwd=REPO,check=True)
subprocess.run(['git','checkout','--detach',REPOSITORY_COMMIT],cwd=REPO,check=True)
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()==REPOSITORY_COMMIT
assert not subprocess.check_output(['git','status','--porcelain'],cwd=REPO,text=True).strip()
lock=WORK/'requirements-kaggle-qci2-cpu.txt'
lines=(REPO/'requirements-lock.txt').read_text(encoding='utf-8').splitlines()
lock.write_text('\\n'.join(line for line in lines if line.strip() and not line.strip().startswith('torch=='))+'\\n',encoding='utf-8')
"""),
        _cell("code", """# Optional resume from one previously downloaded private checkpoint input.
checkpoints=list(Path('/kaggle/input').rglob('aether-qwen-qci2-checkpoint.tar.gz'))
if len(checkpoints)>1: raise RuntimeError(f'Attach at most one checkpoint: {checkpoints}')
if checkpoints:
 with tarfile.open(checkpoints[0],'r:gz') as bundle:
  for member in bundle.getmembers():
   parts=Path(member.name).parts
   if Path(member.name).is_absolute() or '..' in parts or member.issym() or member.islnk(): raise ValueError(f'Unsafe checkpoint member: {member.name}')
  bundle.extractall(WORK,filter='data')
 state=json.loads((OUTPUT/'checkpoint_state.json').read_text())
 print('Resume prefix:',state['completed_executions'],'/ 1920')
else: print('Fresh run; no checkpoint attached.')
"""),
        _cell("code", """# Install qualified CPU dependencies and run all model-free QCI-2 gates.
subprocess.run([UV,'pip','install','--python',str(PY),'pip==25.3'],check=True,env=uv_env)
subprocess.run([UV,'pip','install','--python',str(PY),'torch==2.14.1','--index-url','https://download.pytorch.org/whl/cpu'],check=True,env=uv_env)
subprocess.run([UV,'pip','install','--python',str(PY),'--requirement',str(lock)],check=True,env=uv_env)
subprocess.run([UV,'pip','install','--python',str(PY),'--no-deps','--editable',str(REPO)],check=True,env=uv_env)
run_logged('dependency-check',[str(PY),'-m','pip','check'],cwd=REPO)
run_logged('environment',[str(PY),'-c','import sys,torch; print(sys.version,torch.__version__,torch.version.cuda); assert sys.version_info[:2]==(3,11); assert torch.version.cuda is None and not torch.cuda.is_available()'],cwd=REPO)
run_logged('model-free-qci2-tests',[str(PY),'-m','pytest','tests/unit/test_qci2_execution.py','tests/unit/test_qci2_resume.py','tests/unit/test_qci2_bundle_verifier.py','tests/unit/test_qci_runner.py','tests/unit/test_model_adapter.py','-q'],cwd=REPO)
"""),
        _cell("markdown", """## Pre-access gate

This verifies the retained QCI-1 evidence, frozen QCI-2 protocol, exact candidate
reuse, locked splits, budgets, CPU condition, RAM and disk before model access.
Stop if `overall` is not `PASS`.
"""),
        _cell("code", """run_logged('qci2-preflight',[str(PY),'-m','instrumentation.run_qwen_causal_semantic_interventions',
    '--preflight-only','--output',str(OUTPUT),'--cache',str(HF_CACHE)],cwd=REPO)
preflight=json.loads((OUTPUT/'qci2_preflight.json').read_text())
print(json.dumps(preflight['decision'],indent=2)); print(json.dumps(preflight['hardware']['measurements'],indent=2))
assert preflight['decision']['overall']=='PASS'
"""),
        _cell("markdown", """## One pinned model-snapshot access

The marker defines this as one retained attempt. Never delete it to rerun or tune
the frozen study. If download fails, archive the failure and stop.
"""),
        _cell("code", """marker_path=OUTPUT/'qci2_model_access.json'; resuming=(OUTPUT/'raw_interventions.jsonl').is_file()
if marker_path.exists() and not resuming: raise RuntimeError('Unexpected marker without checkpoint rows')
preflight_path=OUTPUT/'qci2_preflight.json'
marker={'state':'MODEL_SNAPSHOT_RESUME_STARTED' if resuming else 'MODEL_SNAPSHOT_DOWNLOAD_STARTED','model_id':MODEL_ID,'model_revision':MODEL_REVISION,
        'preflight_sha256':hashlib.sha256(preflight_path.read_bytes()).hexdigest(),
        'started_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'resuming':resuming}
marker_path.write_text(json.dumps(marker,indent=2),encoding='utf-8')
snapshot_code=r'''import hashlib,json,sys
from pathlib import Path
from huggingface_hub import snapshot_download
model_id,revision,cache,output=sys.argv[1:]
snapshot=Path(snapshot_download(repo_id=model_id,revision=revision,cache_dir=cache,max_workers=1))
if snapshot.name!=revision: raise RuntimeError(f'Resolved snapshot mismatch: {snapshot.name}')
files=[]
for path in sorted(p for p in snapshot.rglob('*') if p.is_file()):
 h=hashlib.sha256()
 with path.open('rb') as stream:
  for chunk in iter(lambda:stream.read(1024*1024),b''): h.update(chunk)
 files.append({'path':path.relative_to(snapshot).as_posix(),'size':path.stat().st_size,'sha256':h.hexdigest()})
target=Path(output)/'model_snapshot_manifest.json'
target.write_text(json.dumps({'schema_version':'aether.model-snapshot.v1','model_id':model_id,
 'resolved_revision':revision,'snapshot_path':str(snapshot),'files':files},indent=2,sort_keys=True),encoding='utf-8')
'''
code=run_logged('model-snapshot-download',[str(PY),'-c',snapshot_code,MODEL_ID,MODEL_REVISION,str(HF_CACHE),str(OUTPUT)],cwd=REPO,timeout=6*60*60,check=False)
if code==0:
 manifest_path=OUTPUT/'model_snapshot_manifest.json'
 marker.update({'state':'MODEL_FILES_READY','snapshot_manifest_path':str(manifest_path),'snapshot_manifest_sha256':hashlib.sha256(manifest_path.read_bytes()).hexdigest()})
else: marker.update({'state':'MODEL_SNAPSHOT_DOWNLOAD_FAILED','download_exit_code':code})
marker_path.write_text(json.dumps(marker,indent=2),encoding='utf-8')
assert code==0,'Preserve the failed attempt and stop.'
"""),
        _cell("markdown", """## Execute or resume the frozen QCI-2 campaign

Runs 1,920 candidate executions plus 32 whole-message controls. Output is
streamed continuously. Every 25 rows, a checkpoint archive is replaced
atomically in `/kaggle/working`. If interrupted without a session reset, rerun
this cell once; only an exact validated prefix is skipped.
"""),
        _cell("code", """code=run_logged('qwen-qci2-semantic',[str(PY),'-m','instrumentation.run_qwen_causal_semantic_interventions',
    '--output',str(OUTPUT),'--cache',str(HF_CACHE),'--resume'],cwd=REPO,timeout=24*60*60,check=False)
summary_path=OUTPUT/'summary.json'
if summary_path.exists(): print(json.dumps(json.loads(summary_path.read_text()),indent=2))
else:
 failure=OUTPUT/'execution_failure.json'
 if failure.exists(): print(failure.read_text())
 print('No summary exists. Preserve this failed attempt.')
assert code==0,'QCI-2 failed; proceed only to the emergency archive cell.'
"""),
        _cell("code", """# Independently verify, hash and export all evidence except cached model weights.
hashes={}
for path in sorted(p for p in OUTPUT.rglob('*') if p.is_file()):
 hashes[path.relative_to(OUTPUT).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
(OUTPUT/'archive_contents.json').write_text(json.dumps(hashes,indent=2,sort_keys=True),encoding='utf-8')
run_logged('independent-qci2-verification',[str(PY),'-m','scripts.verify_qci2_bundle',str(OUTPUT)],cwd=REPO)
archive=WORK/'aether-qwen-qci2-results.tar.gz'
with tarfile.open(archive,'w:gz') as bundle: bundle.add(OUTPUT,arcname=OUTPUT.name)
print('Archive:',archive); print('SHA-256:',hashlib.sha256(archive.read_bytes()).hexdigest())
print('Final state:',json.loads((OUTPUT/'qci2_model_access.json').read_text())['state'])
"""),
        _cell("markdown", """## Emergency failure archive

Run this cell only if a previous cell failed after creating the output directory.
It preserves the attempt for diagnosis; it does not convert a failure into evidence.
"""),
        _cell("code", """# OPTIONAL FAILURE-ONLY CELL: do not run after a successful export.
if not (WORK/'aether-qwen-qci2-results.tar.gz').exists():
 emergency=WORK/'aether-qwen-qci2-failed-attempt.tar.gz'
 with tarfile.open(emergency,'w:gz') as bundle: bundle.add(OUTPUT,arcname=OUTPUT.name)
 print('Failure archive:',emergency); print('SHA-256:',hashlib.sha256(emergency.read_bytes()).hexdigest())
else: print('Successful archive already exists; no emergency archive created.')
"""),
    ]
    return {
        "cells": cells,
        "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                     "language_info": {"name": "python", "version": "3.13"}},
        "nbformat": 4, "nbformat_minor": 5,
    }


def main() -> None:
    """Write the clean QCI-2 notebook."""
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(build(), indent=1) + "\n", encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
