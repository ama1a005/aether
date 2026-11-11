"""Build the uploadable Kaggle notebook for the frozen QCI-A1 audit."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_URL = "https://github.com/ama1a005/aether.git"
REPOSITORY_COMMIT = "8d5e5d3f30de0b3df2e443b31afca90073fa1d6e"
MODEL_ID = "Qwen/Qwen2.5-1.5B-Instruct"
MODEL_REVISION = "989aa7980e4cf806f80c7fef2b1adb7bc71aa306"
OUTPUT = ROOT / "notebooks/aether_qwen_causal_audit_cpu.ipynb"


def _cell(kind: str, source: str) -> dict[str, object]:
    """Create a stable notebook cell without stored outputs."""
    cell: dict[str, object] = {
        "cell_type": kind,
        "id": hashlib.sha256((kind + source).encode()).hexdigest()[:8],
        "metadata": {},
        "source": source.splitlines(keepends=True),
    }
    if kind == "code":
        cell.update({"execution_count": None, "outputs": []})
    return cell


def build() -> dict[str, object]:
    """Return the ordered one-attempt CPU development-audit notebook."""
    cells = [
        _cell("markdown", """# AETHER Qwen2.5-1.5B QCI development audit (QCI-A1)

Attach the retained `aether-qwen-qci-results.tar.gz` as a private Kaggle input,
enable Internet, and run all cells once. The notebook stops before model access
unless the discovery bundle independently verifies and contains supported
candidates. Validation and test remain locked.
"""),
        _cell("code", f"""from pathlib import Path
import hashlib,json,os,platform,shutil,subprocess,sys,tarfile,time
WORK=Path('/kaggle/working'); RUNTIME=Path('/tmp/aether-qci-audit')
REPO,VENV=RUNTIME/'aether',RUNTIME/'venv'; PY=VENV/'bin'/'python'
HF_CACHE=RUNTIME/'hf-cache'; OUTPUT=WORK/'aether-qci-audit'
for path in (RUNTIME,HF_CACHE,OUTPUT): path.mkdir(parents=True,exist_ok=True)
REPOSITORY_URL={REPOSITORY_URL!r}; REPOSITORY_COMMIT={REPOSITORY_COMMIT!r}
MODEL_ID={MODEL_ID!r}; MODEL_REVISION={MODEL_REVISION!r}
os.environ.update({{'MPLBACKEND':'Agg','PYTHONNOUSERSITE':'1','TOKENIZERS_PARALLELISM':'false',
                   'OMP_NUM_THREADS':'2','MKL_NUM_THREADS':'2','OPENBLAS_NUM_THREADS':'2'}})
for name in ('AETHER_RUN_REAL_MODEL_TESTS','AETHER_RUN_CALIBRATION_MODELS','AETHER_RUN_DEMO_E2E'):
    os.environ.pop(name,None)
def run_logged(name,command,cwd=None,timeout=3600,check=True):
    path=OUTPUT/(name+'.log')
    with path.open('w',encoding='utf-8') as log:
        process=subprocess.Popen(command,cwd=cwd,env=os.environ.copy(),stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT,text=True,bufsize=1)
        assert process.stdout is not None; started=time.monotonic()
        for line in process.stdout:
            print(line,end='',flush=True); log.write(line); log.flush()
            if time.monotonic()-started>timeout:
                process.kill(); process.wait(); raise subprocess.TimeoutExpired(command,timeout)
        return_code=process.wait()
    if check and return_code: raise subprocess.CalledProcessError(return_code,command)
    return return_code
print('Kaggle Python:',sys.version); print('Platform:',platform.platform())
"""),
        _cell("code", """# Locate exactly one retained discovery archive and extract it safely.
archives=list(Path('/kaggle/input').rglob('aether-qwen-qci-results.tar.gz'))
working_archive=WORK/'aether-qwen-qci-results.tar.gz'
if working_archive.is_file(): archives.append(working_archive)
assert len(archives)==1, f'Attach exactly one QCI archive; found {archives}'
DISCOVERY_EXTRACT=RUNTIME/'discovery'; DISCOVERY_EXTRACT.mkdir()
with tarfile.open(archives[0],'r:gz') as bundle:
    for member in bundle.getmembers():
        parts=Path(member.name).parts
        if Path(member.name).is_absolute() or '..' in parts or member.issym() or member.islnk():
            raise ValueError(f'Unsafe archive member: {member.name}')
    bundle.extractall(DISCOVERY_EXTRACT,filter='data')
summaries=list(DISCOVERY_EXTRACT.rglob('summary.json'))
assert len(summaries)==1, f'Expected one discovery summary; found {summaries}'
DISCOVERY=summaries[0].parent
print('Discovery archive:',archives[0]); print('Discovery root:',DISCOVERY)
"""),
        _cell("code", """# Isolated CPython 3.11 and immutable source checkout.
if shutil.which('uv') is None: subprocess.run([sys.executable,'-m','pip','install','uv'],check=True)
UV=shutil.which('uv'); assert UV
uv_env=os.environ.copy(); uv_env['UV_PYTHON_INSTALL_DIR']=str(RUNTIME/'uv-python'); uv_env['UV_CACHE_DIR']=str(RUNTIME/'uv-cache')
if not PY.exists(): subprocess.run([UV,'venv','--python','3.11.9',str(VENV)],check=True,env=uv_env)
if not REPO.exists(): subprocess.run(['git','clone','--branch','lm','--single-branch',REPOSITORY_URL,str(REPO)],check=True)
subprocess.run(['git','fetch','--no-tags','origin','lm'],cwd=REPO,check=True)
subprocess.run(['git','checkout','--detach',REPOSITORY_COMMIT],cwd=REPO,check=True)
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()==REPOSITORY_COMMIT
lock=WORK/'requirements-kaggle-qci-audit-cpu.txt'
lines=(REPO/'requirements-lock.txt').read_text(encoding='utf-8').splitlines()
lock.write_text('\n'.join(line for line in lines if line.strip() and not line.strip().startswith('torch=='))+'\n',encoding='utf-8')
subprocess.run([UV,'pip','install','--python',str(PY),'pip==25.3'],check=True,env=uv_env)
subprocess.run([UV,'pip','install','--python',str(PY),'torch==2.14.1','--index-url','https://download.pytorch.org/whl/cpu'],check=True,env=uv_env)
subprocess.run([UV,'pip','install','--python',str(PY),'--requirement',str(lock)],check=True,env=uv_env)
subprocess.run([UV,'pip','install','--python',str(PY),'--no-deps','--editable',str(REPO)],check=True,env=uv_env)
run_logged('dependency-check',[str(PY),'-m','pip','check'],cwd=REPO)
"""),
        _cell("code", """# Model-independent gates, including discovery-bundle consistency.
run_logged('audit-tests',[str(PY),'-m','pytest','tests/unit/test_qci_execution.py',
    'tests/unit/test_qci_audit.py','tests/unit/test_qci_audit_runner.py',
    'tests/unit/test_qci_bundle_verifier.py','tests/unit/test_model_adapter.py','-q'],cwd=REPO)
run_logged('discovery-verification',[str(PY),'scripts/verify_qci_bundle.py',str(DISCOVERY)],cwd=REPO)
"""),
        _cell("markdown", """## Pre-access authorization gate

This stops without model access if discovery has no supported candidate, any
hash/denominator differs, or hardware fails the qualified CPU condition.
"""),
        _cell("code", """run_logged('audit-preflight',[str(PY),'-m','instrumentation.run_qwen_causal_audit',
    '--preflight-only','--discovery',str(DISCOVERY),'--output',str(OUTPUT),
    '--cache',str(HF_CACHE)],cwd=REPO)
preflight=json.loads((OUTPUT/'audit_preflight.json').read_text())
print(json.dumps(preflight,indent=2)); assert preflight['decision']['overall']=='PASS'
"""),
        _cell("markdown", """## One pinned model-snapshot access

The marker makes this a single retained audit attempt. Preserve failures and do
not delete the marker, replace candidates, or alter thresholds.
"""),
        _cell("code", """marker_path=OUTPUT/'audit_model_access.json'; assert not marker_path.exists()
preflight_path=OUTPUT/'audit_preflight.json'
marker={'state':'MODEL_SNAPSHOT_DOWNLOAD_STARTED','model_id':MODEL_ID,'model_revision':MODEL_REVISION,
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
 h=hashlib.sha256()
 with path.open('rb') as stream:
  for chunk in iter(lambda:stream.read(1024*1024),b''): h.update(chunk)
 files.append({'path':path.relative_to(snapshot).as_posix(),'size':path.stat().st_size,'sha256':h.hexdigest()})
target=Path(output)/'model_snapshot_manifest.json'
target.write_text(json.dumps({'schema_version':'aether.model-snapshot.v1','model_id':model_id,
 'resolved_revision':revision,'snapshot_path':str(snapshot),'files':files},indent=2,sort_keys=True),encoding='utf-8')
'''
exit_code=run_logged('model-snapshot-download',[str(PY),'-c',snapshot_code,MODEL_ID,MODEL_REVISION,str(HF_CACHE),str(OUTPUT)],cwd=REPO,timeout=6*60*60,check=False)
if exit_code==0:
 manifest_path=OUTPUT/'model_snapshot_manifest.json'; marker.update({'state':'MODEL_FILES_READY','snapshot_manifest_path':str(manifest_path),'snapshot_manifest_sha256':hashlib.sha256(manifest_path.read_bytes()).hexdigest()})
else: marker.update({'state':'MODEL_SNAPSHOT_DOWNLOAD_FAILED','download_exit_code':exit_code})
marker_path.write_text(json.dumps(marker,indent=2),encoding='utf-8')
assert exit_code==0,'Preserve the failed attempt and stop.'
"""),
        _cell("code", """# Execute only the frozen four-case development audit.
exit_code=run_logged('qwen-causal-audit',[str(PY),'-m','instrumentation.run_qwen_causal_audit',
    '--discovery',str(DISCOVERY),'--output',str(OUTPUT),'--cache',str(HF_CACHE)],
    cwd=REPO,timeout=12*60*60,check=False)
summary_path=OUTPUT/'summary.json'
if summary_path.exists(): print(json.dumps(json.loads(summary_path.read_text()),indent=2))
else:
 failure=OUTPUT/'execution_failure.json'
 if failure.exists(): print(failure.read_text())
 print('No audit summary exists; preserve this failed attempt.')
"""),
        _cell("code", """# Export retained evidence without model weights.
hashes={}
for path in sorted(p for p in OUTPUT.rglob('*') if p.is_file()):
 hashes[path.relative_to(OUTPUT).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
(OUTPUT/'archive_contents.json').write_text(json.dumps(hashes,indent=2,sort_keys=True),encoding='utf-8')
run_logged('audit-evidence-verification',[str(PY),'scripts/verify_qci_audit_bundle.py',str(OUTPUT)],cwd=REPO)
archive=WORK/'aether-qwen-qci-audit-results.tar.gz'
with tarfile.open(archive,'w:gz') as bundle: bundle.add(OUTPUT,arcname=OUTPUT.name)
print('Archive:',archive); print('SHA-256:',hashlib.sha256(archive.read_bytes()).hexdigest())
print('Final state:',json.loads((OUTPUT/'audit_model_access.json').read_text())['state'])
"""),
    ]
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.13"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def main() -> None:
    """Write the clean QCI-A1 notebook with no execution outputs."""
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(build(), indent=1) + "\n", encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
