"""Build the commit-pinned, restart-safe CORE-02 Kaggle notebook."""

from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "67759734dc841ddd5b0705d5846cb396408e9b84"
OUTPUT = ROOT / "notebooks/aether_qwen_core02_matched_search.ipynb"


def _cell(kind: str, source: str) -> dict[str, object]:
    row: dict[str, object] = {"cell_type": kind, "id": hashlib.sha256(source.encode()).hexdigest()[:8],
                              "metadata": {}, "source": source.splitlines(keepends=True)}
    if kind == "code": row.update({"execution_count": None, "outputs": []})
    return row


def build() -> dict[str, object]:
    cells = [
        _cell("markdown", """# AETHER CORE-02 real Qwen matched search

Runs the approved v2/v2.2/v2.3 development-discovery campaign: five methods,
three seeds, 15 isolated ledgers. It never accesses development-audit,
validation or test. Run all cells with Internet enabled. Download the final
archive, or the checkpoint archive if the session is interrupted.
"""),
        _cell("code", f"""from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,tarfile
WORK=Path('/kaggle/working'); RUNTIME=Path('/tmp/aether-core02')
REPO=RUNTIME/'aether'; VENV=RUNTIME/'venv'; PY=VENV/'bin'/'python'
CACHE=RUNTIME/'hf-cache'; OUTPUT=WORK/'aether-core02-results'
COMMIT={COMMIT!r}; URL='https://github.com/ama1a005/aether.git'
os.environ.update({{'MPLBACKEND':'Agg','PYTHONNOUSERSITE':'1','TOKENIZERS_PARALLELISM':'false','OMP_NUM_THREADS':'2','MKL_NUM_THREADS':'2'}})
for path in (RUNTIME,CACHE): path.mkdir(parents=True,exist_ok=True)
print(sys.version)
"""),
        _cell("code", """# Restore one previously saved checkpoint dataset, if attached.
checkpoints=list(Path('/kaggle/input').rglob('aether-core02-checkpoint.tar.gz'))
if len(checkpoints)>1: raise RuntimeError(f'Attach at most one checkpoint: {checkpoints}')
if checkpoints:
 with tarfile.open(checkpoints[0],'r:gz') as bundle:
  for member in bundle.getmembers():
   if Path(member.name).is_absolute() or '..' in Path(member.name).parts or member.issym() or member.islnk(): raise ValueError(member.name)
  bundle.extractall(WORK,filter='data')
 print('Restored:',checkpoints[0])
else: print('Fresh campaign')
"""),
        _cell("code", """# Install isolated Python 3.11 and immutable source.
if shutil.which('uv') is None: subprocess.run([sys.executable,'-m','pip','install','uv'],check=True)
UV=shutil.which('uv'); env=os.environ.copy(); env['UV_PYTHON_INSTALL_DIR']=str(RUNTIME/'uv-python')
if not PY.exists(): subprocess.run([UV,'venv','--python','3.11.9',str(VENV)],check=True,env=env)
if not REPO.exists(): subprocess.run(['git','clone','--branch','phase1/core-nov19','--single-branch',URL,str(REPO)],check=True)
subprocess.run(['git','fetch','origin','phase1/core-nov19'],cwd=REPO,check=True)
subprocess.run(['git','checkout','--detach',COMMIT],cwd=REPO,check=True)
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()==COMMIT
lock=WORK/'core02-lock.txt'; lines=(REPO/'requirements-lock.txt').read_text().splitlines()
lock.write_text(chr(10).join(x for x in lines if not x.startswith('torch=='))+chr(10))
subprocess.run([UV,'pip','install','--python',str(PY),'torch==2.14.1','--index-url','https://download.pytorch.org/whl/cpu'],check=True,env=env)
subprocess.run([UV,'pip','install','--python',str(PY),'-r',str(lock)],check=True,env=env)
subprocess.run([UV,'pip','install','--python',str(PY),'--no-deps','-e',str(REPO)],check=True,env=env)
subprocess.run([str(PY),'-m','pytest','tests/unit/test_phase1_core_method_freeze.py','tests/unit/test_phase1_core_matched_search.py','tests/unit/test_phase1_core_qwen_evaluator.py','tests/unit/test_model_adapter.py','-q'],cwd=REPO,check=True)
"""),
        _cell("code", """# Download the one pinned model snapshot through the Python 3.11 environment.
revision='989aa7980e4cf806f80c7fef2b1adb7bc71aa306'
code="from huggingface_hub import snapshot_download; print(snapshot_download('Qwen/Qwen2.5-1.5B-Instruct',revision='"+revision+"',cache_dir=r'"+str(CACHE)+"',max_workers=1))"
snapshot=Path(subprocess.check_output([str(PY),'-c',code],text=True).strip())
assert snapshot.name==revision
print(snapshot)
"""),
        _cell("code", """# Model-free preflight. It creates OUTPUT/preflight.json only on PASS.
if not OUTPUT.exists():
 inputs=[]
 import yaml
 proposal=yaml.safe_load((REPO/'configs/phase1_core/qci2_method_freeze_v2.yaml').read_text())
 for record in proposal['evidence_inputs'].values(): inputs += ['--input-artifact',str(REPO/record['path'])]
 command=[str(PY),'-m','experiments.phase1.qci2_matched_search','--preflight-only','--model-snapshot',str(snapshot),'--declared-budget','7360','--output',str(OUTPUT),*inputs]
 subprocess.run(command,cwd=REPO,check=True)
else:
 assert (OUTPUT/'preflight.json').is_file(); print('Using restored passing preflight')
"""),
        _cell("code", """# Execute or resume. A portable checkpoint archive is replaced after every run.
subprocess.run([str(PY),'-m','instrumentation.run_qci2_matched_search','--output',str(OUTPUT),'--model-snapshot',str(snapshot),'--resume'],cwd=REPO,check=True)
subprocess.run([str(PY),'-m','scripts.verify_qci2_matched_search_bundle',str(OUTPUT)],cwd=REPO,check=True)
archive=WORK/'aether-core02-results.tar.gz'
with tarfile.open(archive,'w:gz') as bundle: bundle.add(OUTPUT,arcname=OUTPUT.name)
print('FINAL ARCHIVE',archive,'SHA256',hashlib.sha256(archive.read_bytes()).hexdigest())
"""),
    ]
    return {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}}, "nbformat": 4, "nbformat_minor": 5}


def main() -> None:
    OUTPUT.write_text(json.dumps(build(), indent=1) + "\n", encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__": main()
