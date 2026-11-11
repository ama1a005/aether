"""Build the uploadable Kaggle notebook for Qwen instrumentation acceptance."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_URL = "https://github.com/ama1a005/aether.git"
REPOSITORY_COMMIT = "a9e4630d8b773b4668c699c12b78311edff8973e"
MODEL_ID = "Qwen/Qwen2.5-1.5B-Instruct"
MODEL_REVISION = "989aa7980e4cf806f80c7fef2b1adb7bc71aa306"
OUTPUT = ROOT / "notebooks/aether_qwen_instrumentation_acceptance_cpu.ipynb"


def _cell(kind: str, source: str) -> dict[str, object]:
    """Create one stable notebook cell with no stored execution state."""
    cell_id = hashlib.sha256((kind + source).encode("utf-8")).hexdigest()[:8]
    base: dict[str, object] = {
        "cell_type": kind, "id": cell_id, "metadata": {},
        "source": source.splitlines(keepends=True),
    }
    if kind == "code":
        base.update({"execution_count": None, "outputs": []})
    return base


def build() -> dict[str, object]:
    """Return the ordered, single-attempt CPU instrumentation notebook."""
    cells = [
        _cell("markdown", """# AETHER Qwen2.5-1.5B instrumentation acceptance

This is the separately reviewed stage authorized after MQ-HW1, MQ-G1, and MQ-G2
passed. It verifies passive hook non-interference, selected activation capture,
pre-`o_proj` head semantics, tensor round trips, fixed activation-patch execution,
and hook cleanup on development cases only. It performs no circuit search,
component ranking, remediation, validation, or test evaluation.

Enable Kaggle Internet and run every cell once from top to bottom. The qualified
CPU-float32 numerical condition is preserved; attached GPUs remain unused.
"""),
        _cell("code", f"""from pathlib import Path
import hashlib, json, os, platform, shutil, subprocess, sys, tarfile, time

WORK=Path('/kaggle/working')
RUNTIME=Path('/tmp/aether-qwen-instrumentation')
REPO,VENV=RUNTIME/'aether',RUNTIME/'venv'
PY=VENV/'bin'/'python'
HF_CACHE=RUNTIME/'hf-cache'
OUTPUT=WORK/'aether-qwen-instrumentation-acceptance'
for path in (RUNTIME,HF_CACHE,OUTPUT): path.mkdir(parents=True,exist_ok=True)
REPOSITORY_URL={REPOSITORY_URL!r}
REPOSITORY_COMMIT={REPOSITORY_COMMIT!r}
MODEL_ID,MODEL_REVISION={MODEL_ID!r},{MODEL_REVISION!r}
assert len(REPOSITORY_COMMIT)==40 and all(c in '0123456789abcdef' for c in REPOSITORY_COMMIT)
os.environ.update({{'MPLBACKEND':'Agg','PYTHONNOUSERSITE':'1','TOKENIZERS_PARALLELISM':'false',
                   'OMP_NUM_THREADS':'2','MKL_NUM_THREADS':'2','OPENBLAS_NUM_THREADS':'2'}})
for name in ('AETHER_RUN_REAL_MODEL_TESTS','AETHER_RUN_CALIBRATION_MODELS','AETHER_RUN_DEMO_E2E'):
    os.environ.pop(name,None)

def run_logged(name,command,cwd=None,timeout=3600,check=True):
    path=OUTPUT/(name+'.log')
    with path.open('w',encoding='utf-8') as log:
        result=subprocess.run(command,cwd=cwd,env=os.environ.copy(),stdout=log,
                              stderr=subprocess.STDOUT,text=True,timeout=timeout,check=False)
    print(path.read_text(encoding='utf-8')[-16000:])
    if check: result.check_returncode()
    return result.returncode

print('Kaggle Python:',sys.version)
print('Platform:',platform.platform())
"""),
        _cell("code", """# Create isolated CPython 3.11 without using Kaggle's host Python for AETHER.
if shutil.which('uv') is None:
    subprocess.run([sys.executable,'-m','pip','install','uv'],check=True)
UV=shutil.which('uv'); assert UV
uv_env=os.environ.copy()
uv_env['UV_PYTHON_INSTALL_DIR']=str(RUNTIME/'uv-python')
uv_env['UV_CACHE_DIR']=str(RUNTIME/'uv-cache')
if not PY.exists():
    subprocess.run([UV,'venv','--python','3.11.9',str(VENV)],check=True,env=uv_env)
subprocess.run([str(PY),'-c','import sys; assert sys.version_info[:3]==(3,11,9); print(sys.executable,sys.version)'],check=True)
"""),
        _cell("code", """# Check out the exact source that prospectively froze IA-G1.
if not REPO.exists():
    subprocess.run(['git','clone','--branch','lm','--single-branch',REPOSITORY_URL,str(REPO)],check=True)
subprocess.run(['git','checkout','--detach',REPOSITORY_COMMIT],cwd=REPO,check=True)
actual=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()
assert actual==REPOSITORY_COMMIT
assert not subprocess.check_output(['git','status','--porcelain'],cwd=REPO,text=True).strip()
lock=WORK/'requirements-kaggle-qwen-instrumentation-cpu.txt'
lines=(REPO/'requirements-lock.txt').read_text(encoding='utf-8').splitlines()
lines=[line for line in lines if line.strip() and not line.strip().startswith('torch==')]
lock.write_text('\\n'.join(lines)+'\\n',encoding='utf-8')
print('Pinned AETHER commit:',actual)
"""),
        _cell("code", """# Install the same CPU-only numerical condition as model qualification.
subprocess.run([UV,'pip','install','--python',str(PY),'pip==25.3'],check=True,env=uv_env)
subprocess.run([UV,'pip','install','--python',str(PY),'torch==2.14.1',
                '--index-url','https://download.pytorch.org/whl/cpu'],check=True,env=uv_env)
subprocess.run([UV,'pip','install','--python',str(PY),'--requirement',str(lock)],check=True,env=uv_env)
subprocess.run([UV,'pip','install','--python',str(PY),'--no-deps','--editable',str(REPO)],check=True,env=uv_env)
run_logged('dependency-check',[str(PY),'-m','pip','check'],cwd=REPO)
run_logged('environment',[str(PY),'-c',
    'import sys,torch,transformers; print(sys.version,torch.__version__,transformers.__version__,torch.version.cuda); assert sys.version_info[:2]==(3,11); assert torch.version.cuda is None and not torch.cuda.is_available()'],cwd=REPO)
run_logged('model-free-gate-tests',[str(PY),'-m','pytest',
    'tests/unit/test_instrumentation_acceptance.py','tests/unit/test_model_adapter.py','-q'],cwd=REPO)
"""),
        _cell("markdown", """## IA preflight

This verifies the ingested qualification bundle, exact model revision, fixed
development IDs, hashes, memory, disk, and CPU-only execution before requesting
model files. Stop if it does not pass.
"""),
        _cell("code", """run_logged('ia-preflight',[str(PY),'-m','instrumentation.run_qwen_instrumentation_acceptance',
    '--preflight-only','--output',str(OUTPUT),'--cache',str(HF_CACHE)],cwd=REPO)
preflight=json.loads((OUTPUT/'instrumentation_preflight.json').read_text(encoding='utf-8'))
print(json.dumps(preflight,indent=2))
assert preflight['decision']['overall']=='PASS', 'IA preflight blocked; do not access Qwen.'
"""),
        _cell("markdown", """## Pinned snapshot access

This is one model-access attempt for the separately authorized instrumentation
stage. It downloads and hashes the exact already-qualified revision. Preserve
any failure; do not delete the marker and retry.
"""),
        _cell("code", """marker_path=OUTPUT/'instrumentation_model_access.json'
assert not marker_path.exists(),f'Instrumentation attempt already exists: {marker_path}'
preflight_path=OUTPUT/'instrumentation_preflight.json'
marker={'state':'MODEL_SNAPSHOT_DOWNLOAD_STARTED','model_id':MODEL_ID,
        'model_revision':MODEL_REVISION,
        'preflight_sha256':hashlib.sha256(preflight_path.read_bytes()).hexdigest(),
        'started_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
marker_path.write_text(json.dumps(marker,indent=2),encoding='utf-8')
snapshot_code=r'''import hashlib,json,sys
from pathlib import Path
from huggingface_hub import snapshot_download
model_id,revision,cache,output=sys.argv[1:]
snapshot=Path(snapshot_download(repo_id=model_id,revision=revision,cache_dir=cache,max_workers=1))
if snapshot.name!=revision: raise RuntimeError(f'Resolved snapshot mismatch: {snapshot.name}')
files=[]
for path in sorted(p for p in snapshot.rglob('*') if p.is_file()):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''): digest.update(chunk)
    files.append({'path':path.relative_to(snapshot).as_posix(),'size':path.stat().st_size,
                  'sha256':digest.hexdigest()})
required={'config.json','model.safetensors','tokenizer.json','tokenizer_config.json'}
names={record['path'] for record in files}
if not required<=names: raise RuntimeError(f'Missing snapshot files: {sorted(required-names)}')
target=Path(output)/'model_snapshot_manifest.json'
target.write_text(json.dumps({'schema_version':'aether.model-snapshot.v1','model_id':model_id,
    'resolved_revision':revision,'snapshot_path':str(snapshot),'files':files},indent=2,sort_keys=True),encoding='utf-8')
'''
exit_code=run_logged('model-snapshot-download',[str(PY),'-c',snapshot_code,MODEL_ID,
    MODEL_REVISION,str(HF_CACHE),str(OUTPUT)],cwd=REPO,timeout=6*60*60,check=False)
if exit_code==0:
    snapshot_manifest=OUTPUT/'model_snapshot_manifest.json'
    marker.update({'state':'MODEL_FILES_READY','snapshot_manifest_path':str(snapshot_manifest),
                   'snapshot_manifest_sha256':hashlib.sha256(snapshot_manifest.read_bytes()).hexdigest()})
else:
    marker.update({'state':'MODEL_SNAPSHOT_DOWNLOAD_FAILED','download_exit_code':exit_code})
marker_path.write_text(json.dumps(marker,indent=2),encoding='utf-8')
assert exit_code==0,'Snapshot access failed; preserve outputs and stop.'
"""),
        _cell("markdown", """## Execute IA-G1

The runner loads Qwen once, executes only the prospectively selected checks,
writes raw measurements and activation artifacts, and stops. A PASS authorizes
protocol review for later development capture; it is not circuit evidence.
"""),
        _cell("code", """exit_code=run_logged('qwen-instrumentation-acceptance',
    [str(PY),'-m','instrumentation.run_qwen_instrumentation_acceptance',
     '--output',str(OUTPUT),'--cache',str(HF_CACHE)],cwd=REPO,timeout=24*60*60,check=False)
summary_path=OUTPUT/'summary.json'
if summary_path.exists():
    summary=json.loads(summary_path.read_text(encoding='utf-8'))
    print(json.dumps(summary,indent=2))
else:
    failure=OUTPUT/'execution_failure.json'
    if failure.exists(): print(failure.read_text(encoding='utf-8'))
    print('No summary exists; preserve the failed attempt.')
"""),
        _cell("code", """# Hash every output and create one downloadable archive; weights remain in /tmp.
hashes={}
for path in sorted(p for p in OUTPUT.rglob('*') if p.is_file()):
    hashes[path.relative_to(OUTPUT).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
(OUTPUT/'archive_contents.json').write_text(json.dumps(hashes,indent=2,sort_keys=True),encoding='utf-8')
archive=WORK/'aether-qwen-instrumentation-acceptance-results.tar.gz'
with tarfile.open(archive,'w:gz') as bundle:
    bundle.add(OUTPUT,arcname=OUTPUT.name)
archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest()
print('Archive:',archive)
print('SHA-256:',archive_sha256)
print('Final state:',json.loads((OUTPUT/'instrumentation_model_access.json').read_text())['state'])
"""),
    ]
    return {
        "cells": cells,
        "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                     "language_info": {"name": "python", "version": "3.13"}},
        "nbformat": 4, "nbformat_minor": 5,
    }


def main() -> None:
    """Write a clean instrumentation notebook with no execution outputs."""
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(build(), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
