"""Build the commit-pinned Kaggle notebook for SmolLM2 qualification."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "notebooks/aether_smollm2_second_model_qualification.ipynb"
COMMIT = "9f9bb8ee37474aa1cd9f0e562ff60fbfda2eda88"

def cell(kind: str, source: str) -> dict:
    """Construct one notebook cell."""
    base = {"cell_type": kind, "metadata": {}, "source": [line + "\n" for line in source.splitlines()]}
    if kind == "code": base.update({"execution_count": None, "outputs": []})
    return base

def build() -> None:
    """Write the ordered notebook without outputs."""
    cells = [
        cell("markdown", "# AETHER SmolLM2 second-model qualification\n\nRun all cells in order on Kaggle CPU with Internet enabled. A PASS or FAIL is retained; validation and test remain closed."),
        cell("code", f'''from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,tarfile,time
WORK=Path('/kaggle/working'); RUNTIME=Path('/tmp/aether-smollm2'); REPO=RUNTIME/'aether'; VENV=RUNTIME/'venv'; PY=VENV/'bin/python'
OUTPUT=WORK/'aether-smollm2-qualification'; CACHE=RUNTIME/'hf-cache'
URL='https://github.com/ama1a005/aether.git'; COMMIT='{COMMIT}'
if RUNTIME.exists(): shutil.rmtree(RUNTIME)
RUNTIME.mkdir(); OUTPUT.mkdir(exist_ok=True); CACHE.mkdir()
if shutil.which('uv') is None: subprocess.run([sys.executable,'-m','pip','install','uv'],check=True)
UV=shutil.which('uv'); env=os.environ.copy(); env['UV_PYTHON_INSTALL_DIR']=str(RUNTIME/'uv-python')
subprocess.run([UV,'venv','--python','3.11.9',str(VENV)],check=True,env=env)
subprocess.run(['git','clone','--branch','m3/mech-interventions','--single-branch',URL,str(REPO)],check=True)
subprocess.run(['git','checkout','--detach',COMMIT],cwd=REPO,check=True)
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()==COMMIT
lock=RUNTIME/'lock.txt'; lock.write_text('\\n'.join(x for x in (REPO/'requirements-lock.txt').read_text().splitlines() if not x.startswith('torch=='))+'\\n')
subprocess.run([UV,'pip','install','--python',str(PY),'torch==2.14.1','--index-url','https://download.pytorch.org/whl/cpu'],check=True,env=env)
subprocess.run([UV,'pip','install','--python',str(PY),'-r',str(lock)],check=True,env=env)
subprocess.run([UV,'pip','install','--python',str(PY),'--no-deps','-e',str(REPO)],check=True,env=env)
subprocess.run([str(PY),'-m','pytest','tests/unit/test_secondary_model_freeze.py','tests/unit/test_secondary_model_qualification.py','tests/unit/test_model_adapter.py','-q'],cwd=REPO,check=True)'''),
        cell("code", '''# Preflight is model-free and must pass before download.
preflight_run=subprocess.run([str(PY),'-m','paired_trace.run_secondary_model_qualification','--preflight-only','--output',str(OUTPUT),'--cache',str(CACHE)],cwd=REPO,check=False)
preflight_path=OUTPUT/'hardware_preflight.json'
if preflight_path.is_file(): print(preflight_path.read_text(encoding='utf-8'))
if preflight_run.returncode: raise RuntimeError(f'SmolLM2 preflight blocked with exit code {preflight_run.returncode}; inspect the JSON printed above')'''),
        cell("code", '''# Download and hash the immutable snapshot, then create the required access marker.
code=r"""import hashlib,json,sys
from pathlib import Path
from huggingface_hub import snapshot_download
model,revision,cache,out=sys.argv[1:]
snapshot=Path(snapshot_download(repo_id=model,revision=revision,cache_dir=cache,max_workers=2))
files=[]
for p in sorted(x for x in snapshot.rglob('*') if x.is_file()):
 h=hashlib.sha256(p.read_bytes()).hexdigest(); files.append({'path':p.relative_to(snapshot).as_posix(),'size':p.stat().st_size,'sha256':h})
target=Path(out)/'model_snapshot_manifest.json'; target.write_text(json.dumps({'model_id':model,'resolved_revision':revision,'snapshot_path':str(snapshot),'files':files},indent=2))
"""
MODEL='HuggingFaceTB/SmolLM2-1.7B-Instruct'; REV='dfc017ec3d4e0eaed394f8bf2a0fd2ff24f8b2cd'
subprocess.run([str(PY),'-c',code,MODEL,REV,str(CACHE),str(OUTPUT)],check=True)
pre=OUTPUT/'hardware_preflight.json'; snap=OUTPUT/'model_snapshot_manifest.json'
marker={'state':'MODEL_FILES_READY','model_id':MODEL,'model_revision':REV,'hardware_preflight_sha256':hashlib.sha256(pre.read_bytes()).hexdigest(),'snapshot_manifest_path':str(snap),'snapshot_manifest_sha256':hashlib.sha256(snap.read_bytes()).hexdigest()}
(OUTPUT/'model_access_attempt_started.json').write_text(json.dumps(marker,indent=2))
print(marker['state'])'''),
        cell("code", '''# Execute behavioral gates, then instrumentation only after behavioral PASS.
log=WORK/'aether-smollm2-execution.log'
with log.open('w',encoding='utf-8') as stream:
 process=subprocess.Popen([str(PY),'-u','-m','paired_trace.run_secondary_model_qualification','--output',str(OUTPUT),'--cache',str(CACHE)],cwd=REPO,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
 for line in process.stdout:
  print(line,end=''); stream.write(line); stream.flush()
 code=process.wait()
print('exit_code',code)
if code: print(log.read_text(encoding='utf-8')[-16000:])'''),
        cell("code", '''# Verify even a scientifically negative complete result; failures remain visible.
summary=OUTPUT/'summary.json'
assert summary.is_file(),'No complete summary: inspect execution.log and preserve the directory.'
subprocess.run([str(PY),'-m','scripts.verify_secondary_model_bundle',str(OUTPUT)],cwd=REPO,check=True)
print(summary.read_text(encoding='utf-8'))'''),
        cell("code", '''# Export a verified archive. Download from the Kaggle Output panel.
archive=WORK/'aether-smollm2-qualification-results.tar.gz'
with tarfile.open(archive,'w:gz') as bundle: bundle.add(OUTPUT,arcname=OUTPUT.name)
print(archive,archive.stat().st_size)'''),
    ]
    OUTPUT.write_text(json.dumps({"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}}, "nbformat": 4, "nbformat_minor": 5}, indent=1), encoding="utf-8")

if __name__ == "__main__": build()
