"""Build the uploadable Kaggle notebook for frozen CPU Qwen qualification."""
from __future__ import annotations

import json
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_URL = "https://github.com/ama1a005/aether.git"
REPOSITORY_COMMIT = "ed6a9ab742426d45626b63c211642079af9f1a97"
MODEL_ID = "Qwen/Qwen2.5-1.5B-Instruct"
MODEL_REVISION = "989aa7980e4cf806f80c7fef2b1adb7bc71aa306"
OUTPUT = ROOT / "notebooks/aether_qwen_qualification_cpu.ipynb"


def _cell(kind: str, source: str) -> dict[str, object]:
    cell_id = hashlib.sha256((kind + source).encode("utf-8")).hexdigest()[:8]
    if kind == "markdown":
        return {"cell_type": kind, "id": cell_id, "metadata": {}, "source": source.splitlines(keepends=True)}
    return {"cell_type": kind, "id": cell_id, "execution_count": None, "metadata": {}, "outputs": [],
            "source": source.splitlines(keepends=True)}


def build() -> dict[str, object]:
    """Create an ordered, one-attempt CPU qualification notebook."""
    cells = [
        _cell("markdown", """# AETHER: real Qwen2.5-1.5B qualification on Kaggle

Runs frozen CPU float32 MQ-HW1, MQ-G1 and conditional MQ-G2 on the 24 V2
development cases. It does not run internal hooks/interventions or access
validation/test. If both gates pass, it stops for separate instrumentation
review. Kaggle Internet must be enabled. GPU is intentionally unused to preserve
the frozen CPU protocol. Run cells top-to-bottom once; the output marker blocks
second attempts. Model weights live in `/tmp`, outside the result archive.
"""),
        _cell("code", f"""from pathlib import Path
import hashlib, json, os, platform, shutil, subprocess, sys, time

WORK = Path('/kaggle/working')
RUNTIME = Path('/tmp/aether-qwen-qualification')
REPO, VENV = RUNTIME / 'aether', RUNTIME / 'venv'
PY = VENV / 'bin' / 'python'
HF_CACHE = RUNTIME / 'hf-cache'
OUTPUT = WORK / 'aether-qwen-qualification'
for path in (RUNTIME, HF_CACHE, OUTPUT): path.mkdir(parents=True, exist_ok=True)
REPOSITORY_URL = {REPOSITORY_URL!r}
REPOSITORY_COMMIT = {REPOSITORY_COMMIT!r}
MODEL_ID, MODEL_REVISION = {MODEL_ID!r}, {MODEL_REVISION!r}
assert len(REPOSITORY_COMMIT) == 40 and all(c in '0123456789abcdef' for c in REPOSITORY_COMMIT)
os.environ.update({{'MPLBACKEND':'Agg','PYTHONNOUSERSITE':'1','TOKENIZERS_PARALLELISM':'false',
                   'OMP_NUM_THREADS':'2','MKL_NUM_THREADS':'2','OPENBLAS_NUM_THREADS':'2'}})
for name in ('AETHER_RUN_REAL_MODEL_TESTS','AETHER_RUN_CALIBRATION_MODELS','AETHER_RUN_DEMO_E2E'):
    os.environ.pop(name, None)

def run_logged(name, command, cwd=None, timeout=3600, check=True):
    path = OUTPUT / (name + '.log')
    with path.open('w', encoding='utf-8') as log:
        try: result = subprocess.run(command, cwd=cwd, env=os.environ.copy(), stdout=log,
                                     stderr=subprocess.STDOUT, text=True, timeout=timeout, check=False)
        except subprocess.TimeoutExpired:
            print(path.read_text(encoding='utf-8')[-16000:]); raise
    print(path.read_text(encoding='utf-8')[-16000:])
    if check: result.check_returncode()
    return result.returncode

print('Kaggle Python:', sys.version)
print('Platform:', platform.platform())
"""),
        _cell("code", """# Isolated CPython 3.11.9; all disposable files stay outside notebook output.
if shutil.which('uv') is None:
    subprocess.run([sys.executable, '-m', 'pip', 'install', 'uv'], check=True)
UV = shutil.which('uv'); assert UV
uv_env = os.environ.copy()
uv_env['UV_PYTHON_INSTALL_DIR'] = str(RUNTIME / 'uv-python')
uv_env['UV_CACHE_DIR'] = str(RUNTIME / 'uv-cache')
if not PY.exists(): subprocess.run([UV, 'venv', '--python', '3.11.9', str(VENV)], check=True, env=uv_env)
subprocess.run([str(PY), '-c', 'import sys; assert sys.version_info[:3]==(3,11,9); print(sys.executable,sys.version)'], check=True)
"""),
        _cell("code", f"""# Pin AETHER source and prepare the checked-in lock for CPU-only torch.
if not REPO.exists(): subprocess.run(['git','clone','--branch','lm','--single-branch',REPOSITORY_URL,str(REPO)],check=True)
subprocess.run(['git','checkout','--detach',REPOSITORY_COMMIT],cwd=REPO,check=True)
actual = subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()
assert actual == REPOSITORY_COMMIT
assert not subprocess.check_output(['git','status','--porcelain'],cwd=REPO,text=True).strip()
lock = WORK / 'requirements-kaggle-qwen-cpu.txt'
lines = (REPO/'requirements-lock.txt').read_text(encoding='utf-8').splitlines()
lines = [line for line in lines if line.strip() and not line.strip().startswith('torch==')]
assert not any(line.strip().startswith('torch==') for line in lines)
lock.write_text('\\n'.join(lines)+'\\n',encoding='utf-8')
print('Pinned AETHER commit:', actual)
"""),
        _cell("code", """# Install CPU torch and locked dependencies; no model is accessed in setup.
subprocess.run([UV,'pip','install','--python',str(PY),'pip==25.3'],check=True,env=uv_env)
subprocess.run([UV,'pip','install','--python',str(PY),'torch==2.14.1',
                '--index-url','https://download.pytorch.org/whl/cpu'],check=True,env=uv_env)
subprocess.run([UV,'pip','install','--python',str(PY),'--requirement',str(lock)],check=True,env=uv_env)
subprocess.run([UV,'pip','install','--python',str(PY),'--no-deps','--editable',str(REPO)],check=True,env=uv_env)
run_logged('dependency-check',[str(PY),'-m','pip','check'],cwd=REPO)
run_logged('environment',[str(PY),'-c','import sys,torch,transformers; print(sys.version,torch.__version__,transformers.__version__,torch.version.cuda); assert sys.version_info[:2]==(3,11); assert torch.version.cuda is None and not torch.cuda.is_initialized() and not torch.cuda.is_available()'],cwd=REPO)
"""),
        _cell("markdown", """## MQ-HW1 — pre-access resource gate

The next cell checks hardware and repository metadata only. It does not request
any Qwen files. If this gate blocks, stop and do not run the model-download cell.
"""),
        _cell("code", """run_logged('mq-hw1-preflight',[str(PY),'-m','paired_trace.run_model_qualification',
    '--preflight-only','--output',str(OUTPUT),'--cache',str(HF_CACHE)],cwd=REPO)
hardware = json.loads((OUTPUT/'hardware_preflight.json').read_text(encoding='utf-8'))
print(json.dumps(hardware,indent=2))
assert hardware['decision']['overall']=='PASS', 'MQ-HW1 blocked; do not access Qwen.'
"""),
        _cell("markdown", """## Pinned model download — one attempt

This is the first Qwen repository access. A persistent marker is written before
download. If interrupted, preserve the marker and outputs; do not retry or reset
it. The official model revision is immutable and separately recorded below.
"""),
        _cell("code", """marker_path = OUTPUT/'model_access_attempt_started.json'
assert not marker_path.exists(), f'Single-attempt marker already exists: {marker_path}'
hardware = json.loads((OUTPUT/'hardware_preflight.json').read_text(encoding='utf-8'))
assert hardware['decision']['overall']=='PASS' and hardware['model_accessed'] is False
marker = {'state':'MODEL_SNAPSHOT_DOWNLOAD_STARTED','model_id':MODEL_ID,'model_revision':MODEL_REVISION,
          'hardware_preflight_sha256':hashlib.sha256((OUTPUT/'hardware_preflight.json').read_bytes()).hexdigest(),
          'started_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
marker_path.write_text(json.dumps(marker,indent=2),encoding='utf-8')

snapshot_code = r'''import hashlib,json,sys
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
    files.append({'path':path.relative_to(snapshot).as_posix(),'size':path.stat().st_size,'sha256':digest.hexdigest()})
names={item['path'] for item in files}
required={'config.json','model.safetensors','tokenizer.json','tokenizer_config.json'}
if not required<=names: raise RuntimeError(f'Missing snapshot files: {sorted(required-names)}')
manifest={'schema_version':'aether.model-snapshot.v1','model_id':model_id,'resolved_revision':revision,
          'snapshot_path':str(snapshot),'files':files}
target=Path(output)/'model_snapshot_manifest.json'
target.write_text(json.dumps(manifest,indent=2,sort_keys=True),encoding='utf-8')
print(json.dumps({'snapshot_path':str(snapshot),'file_count':len(files),'manifest_path':str(target)},indent=2))
'''
snapshot_exit=run_logged('model-snapshot-download',[str(PY),'-c',snapshot_code,MODEL_ID,MODEL_REVISION,str(HF_CACHE),str(OUTPUT)],cwd=REPO,timeout=6*60*60,check=False)
if snapshot_exit == 0:
    manifest_path=OUTPUT/'model_snapshot_manifest.json'
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    marker.update({'state':'MODEL_FILES_READY','snapshot_manifest_path':str(manifest_path),
                   'snapshot_manifest_sha256':hashlib.sha256(manifest_path.read_bytes()).hexdigest()})
    print('Pinned snapshot:',manifest['resolved_revision'])
else:
    marker.update({'state':'MODEL_SNAPSHOT_DOWNLOAD_FAILED','download_exit_code':snapshot_exit})
    print('Snapshot failed; preserve this single-attempt failure and do not retry.')
marker_path.write_text(json.dumps(marker,indent=2),encoding='utf-8')
"""),
        _cell("markdown", """## MQ-G1 and conditional MQ-G2

The runner makes one CPU float32 load. It records load failures and post-load
memory. It installs no activation hooks. MQ-G2 executes only when every MQ-G1
predicate passes. A failure is a result and ends this campaign; do not tune and
rerun on the same frozen cases.
"""),
        _cell("code", """marker=json.loads((OUTPUT/'model_access_attempt_started.json').read_text(encoding='utf-8'))
summary=None
if marker['state']=='MODEL_FILES_READY':
    campaign_exit=run_logged('qwen-mq-campaign',[str(PY),'-m','paired_trace.run_model_qualification',
        '--output',str(OUTPUT),'--cache',str(HF_CACHE)],cwd=REPO,timeout=24*60*60,check=False)
else:
    campaign_exit=1
    print('Qualification skipped because the pinned snapshot did not complete.')
summary_path=OUTPUT/'summary.json'
if summary_path.exists():
    summary=json.loads(summary_path.read_text(encoding='utf-8'))
    print(json.dumps(summary,indent=2))
else:
    failure=OUTPUT/'execution_failure.json'
    if failure.exists(): print(failure.read_text(encoding='utf-8'))
    print('No final summary exists; preserve the failure log and marker.')
"""),
        _cell("code", """# Export only qualification data and logs; the 3.1 GB snapshot stays in /tmp.
import tarfile
archive=WORK/'aether-qwen-qualification-results.tar.gz'
with tarfile.open(archive,'w:gz') as tar:
    for path in sorted(OUTPUT.rglob('*')):
        if path.is_file(): tar.add(path,arcname=path.relative_to(OUTPUT).as_posix())
print('Kaggle output archive:',archive)
print('Qualification decision:',summary['decision'] if summary else 'NO FINAL SUMMARY; failure artifacts archived')
"""),
        _cell("code", """# Fail only after output artifacts have been archived and are visible for download.
assert campaign_exit == 0 and summary is not None, 'Download and preserve the archived failure output.'
"""),
        _cell("markdown", """## Stop rule

If MQ-G1 or MQ-G2 fails, preserve the outputs and do not change model, prompt,
parser, cases, seed, precision or thresholds. If both pass, stop for a separately
reviewed instrumentation-acceptance stage. This is a qualification result, not
a publication-ready internal causal-circuit result.
"""),
    ]
    return {"cells": cells, "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.13"}},
        "nbformat": 4, "nbformat_minor": 5}


def main() -> None:
    """Write a clean notebook with no stored execution outputs."""
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(build(), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
