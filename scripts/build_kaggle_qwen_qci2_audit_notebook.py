"""Build the conditional Kaggle notebook for frozen QCI-2A1 audit."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_URL = "https://github.com/ama1a005/aether.git"
REPOSITORY_COMMIT = "f26a3f0c932c652cc86d628fe6ac18bc9b08391a"
MODEL_ID = "Qwen/Qwen2.5-1.5B-Instruct"
MODEL_REVISION = "989aa7980e4cf806f80c7fef2b1adb7bc71aa306"
OUTPUT = ROOT / "notebooks/aether_qwen_qci2_semantic_audit_cpu.ipynb"


def _cell(kind: str, source: str) -> dict[str, object]:
    """Create one deterministic notebook cell without outputs."""
    cell: dict[str, object] = {"cell_type": kind,
        "id": hashlib.sha256((kind + source).encode()).hexdigest()[:8],
        "metadata": {}, "source": source.splitlines(keepends=True)}
    if kind == "code": cell.update({"execution_count": None, "outputs": []})
    return cell


def build() -> dict[str, object]:
    """Return the fail-closed QCI-2A1 one-attempt notebook."""
    cells = [
        _cell("markdown", """# AETHER QCI-2A1 semantic development audit

Run only after attaching the retained `aether-qwen-qci2-results.tar.gz` as a
private Kaggle input. This notebook independently verifies discovery and stops
before model access unless at least one candidate passed every frozen QCI-2
predicate. It accesses four untouched development cases only. Validation and
test remain locked. A negative discovery result means this notebook must stop.
"""),
        _cell("code", f"""from pathlib import Path
import hashlib,json,os,platform,shutil,subprocess,sys,tarfile,time
WORK=Path('/kaggle/working'); RUNTIME=Path('/tmp/aether-qci2-audit')
REPO,VENV=RUNTIME/'aether',RUNTIME/'venv'; PY=VENV/'bin'/'python'
HF_CACHE=RUNTIME/'hf-cache'; OUTPUT=WORK/'aether-qci2-audit'
for path in (RUNTIME,HF_CACHE,OUTPUT): path.mkdir(parents=True,exist_ok=True)
REPOSITORY_URL={REPOSITORY_URL!r}; REPOSITORY_COMMIT={REPOSITORY_COMMIT!r}
MODEL_ID={MODEL_ID!r}; MODEL_REVISION={MODEL_REVISION!r}
os.environ.update({{'MPLBACKEND':'Agg','PYTHONNOUSERSITE':'1','TOKENIZERS_PARALLELISM':'false','OMP_NUM_THREADS':'2','MKL_NUM_THREADS':'2','OPENBLAS_NUM_THREADS':'2'}})
def run_logged(name,command,cwd=None,timeout=3600,check=True):
 path=OUTPUT/(name+'.log')
 with path.open('w',encoding='utf-8') as log:
  process=subprocess.Popen(command,cwd=cwd,env=os.environ.copy(),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
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
print(sys.version); print(platform.platform())
"""),
        _cell("code", """# Locate and safely extract exactly one retained QCI-2 discovery archive.
archives=list(Path('/kaggle/input').rglob('aether-qwen-qci2-results.tar.gz'))
if (WORK/'aether-qwen-qci2-results.tar.gz').is_file(): archives.append(WORK/'aether-qwen-qci2-results.tar.gz')
assert len(archives)==1,f'Attach exactly one QCI-2 result archive; found {archives}'
EXTRACT=RUNTIME/'discovery'; EXTRACT.mkdir()
with tarfile.open(archives[0],'r:gz') as bundle:
 for member in bundle.getmembers():
  parts=Path(member.name).parts
  if Path(member.name).is_absolute() or '..' in parts or member.issym() or member.islnk(): raise ValueError(f'Unsafe member: {member.name}')
 bundle.extractall(EXTRACT,filter='data')
summaries=list(EXTRACT.rglob('summary.json')); assert len(summaries)==1
DISCOVERY=summaries[0].parent
print('Discovery:',DISCOVERY)
"""),
        _cell("code", """# Immutable Python 3.11 environment and source checkout.
if shutil.which('uv') is None: subprocess.run([sys.executable,'-m','pip','install','uv'],check=True)
UV=shutil.which('uv'); assert UV
uv_env=os.environ.copy(); uv_env['UV_PYTHON_INSTALL_DIR']=str(RUNTIME/'uv-python'); uv_env['UV_CACHE_DIR']=str(RUNTIME/'uv-cache')
if not PY.exists(): subprocess.run([UV,'venv','--python','3.11.9',str(VENV)],check=True,env=uv_env)
if not REPO.exists(): subprocess.run(['git','clone','--branch','lm','--single-branch',REPOSITORY_URL,str(REPO)],check=True)
subprocess.run(['git','fetch','--no-tags','origin','lm'],cwd=REPO,check=True)
subprocess.run(['git','checkout','--detach',REPOSITORY_COMMIT],cwd=REPO,check=True)
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()==REPOSITORY_COMMIT
assert not subprocess.check_output(['git','status','--porcelain'],cwd=REPO,text=True).strip()
lock=WORK/'requirements-kaggle-qci2-audit-cpu.txt'
lines=(REPO/'requirements-lock.txt').read_text(encoding='utf-8').splitlines()
lock.write_text('\\n'.join(line for line in lines if line.strip() and not line.strip().startswith('torch=='))+'\\n',encoding='utf-8')
subprocess.run([UV,'pip','install','--python',str(PY),'pip==25.3'],check=True,env=uv_env)
subprocess.run([UV,'pip','install','--python',str(PY),'torch==2.14.1','--index-url','https://download.pytorch.org/whl/cpu'],check=True,env=uv_env)
subprocess.run([UV,'pip','install','--python',str(PY),'--requirement',str(lock)],check=True,env=uv_env)
subprocess.run([UV,'pip','install','--python',str(PY),'--no-deps','--editable',str(REPO)],check=True,env=uv_env)
run_logged('dependency-check',[str(PY),'-m','pip','check'],cwd=REPO)
"""),
        _cell("code", """# Model-free audit and discovery-evidence gates.
run_logged('audit-tests',[str(PY),'-m','pytest','tests/unit/test_qci2_audit.py','tests/unit/test_qci2_audit_runner.py','tests/unit/test_qci2_audit_bundle_verifier.py','tests/unit/test_qci2_bundle_verifier.py','tests/unit/test_model_adapter.py','-q'],cwd=REPO)
run_logged('discovery-verification',[str(PY),'-m','scripts.verify_qci2_bundle',str(DISCOVERY)],cwd=REPO)
"""),
        _cell("code", """# Authorization and hardware preflight; negative discovery stops here.
run_logged('audit-preflight',[str(PY),'-m','instrumentation.run_qwen_causal_semantic_audit','--preflight-only','--discovery',str(DISCOVERY),'--output',str(OUTPUT),'--cache',str(HF_CACHE)],cwd=REPO)
preflight=json.loads((OUTPUT/'audit_preflight.json').read_text())
print(json.dumps(preflight['decision'],indent=2)); assert preflight['decision']['overall']=='PASS'
"""),
        _cell("code", """# One pinned snapshot access after authorization.
marker_path=OUTPUT/'audit_model_access.json'; assert not marker_path.exists()
preflight_path=OUTPUT/'audit_preflight.json'
marker={'state':'MODEL_SNAPSHOT_DOWNLOAD_STARTED','model_id':MODEL_ID,'model_revision':MODEL_REVISION,'preflight_sha256':hashlib.sha256(preflight_path.read_bytes()).hexdigest(),'started_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
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
target=Path(output)/'model_snapshot_manifest.json'; target.write_text(json.dumps({'schema_version':'aether.model-snapshot.v1','model_id':model_id,'resolved_revision':revision,'snapshot_path':str(snapshot),'files':files},indent=2,sort_keys=True),encoding='utf-8')
'''
code=run_logged('model-snapshot-download',[str(PY),'-c',snapshot_code,MODEL_ID,MODEL_REVISION,str(HF_CACHE),str(OUTPUT)],cwd=REPO,timeout=6*60*60,check=False)
if code==0:
 manifest_path=OUTPUT/'model_snapshot_manifest.json'; marker.update({'state':'MODEL_FILES_READY','snapshot_manifest_path':str(manifest_path),'snapshot_manifest_sha256':hashlib.sha256(manifest_path.read_bytes()).hexdigest()})
else: marker.update({'state':'MODEL_SNAPSHOT_DOWNLOAD_FAILED','download_exit_code':code})
marker_path.write_text(json.dumps(marker,indent=2),encoding='utf-8'); assert code==0
"""),
        _cell("code", """# Execute only the authorized four-case development audit.
code=run_logged('qci2-semantic-audit',[str(PY),'-m','instrumentation.run_qwen_causal_semantic_audit','--discovery',str(DISCOVERY),'--output',str(OUTPUT),'--cache',str(HF_CACHE)],cwd=REPO,timeout=12*60*60,check=False)
if (OUTPUT/'summary.json').is_file(): print(json.dumps(json.loads((OUTPUT/'summary.json').read_text()),indent=2))
else:
 if (OUTPUT/'execution_failure.json').is_file(): print((OUTPUT/'execution_failure.json').read_text())
 print('No audit summary; preserve the failed attempt.')
assert code==0
"""),
        _cell("code", """# Verify and export audit evidence.
hashes={path.relative_to(OUTPUT).as_posix():hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(p for p in OUTPUT.rglob('*') if p.is_file())}
(OUTPUT/'archive_contents.json').write_text(json.dumps(hashes,indent=2,sort_keys=True),encoding='utf-8')
run_logged('audit-verification',[str(PY),'-m','scripts.verify_qci2_audit_bundle',str(OUTPUT)],cwd=REPO)
archive=WORK/'aether-qwen-qci2-audit-results.tar.gz'
with tarfile.open(archive,'w:gz') as bundle: bundle.add(OUTPUT,arcname=OUTPUT.name)
print(archive); print(hashlib.sha256(archive.read_bytes()).hexdigest())
"""),
    ]
    return {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python", "version": "3.13"}}, "nbformat": 4, "nbformat_minor": 5}


def main() -> None:
    """Write the clean QCI-2A1 notebook."""
    OUTPUT.write_text(json.dumps(build(), indent=1) + "\n", encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__": main()
