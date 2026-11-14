"""Build three commit-pinned, restart-safe CORE-02 seed-shard notebooks."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "5a29be4826e90fa58affeac4faf015561cefc7dd"


def _cell(kind: str, source: str) -> dict[str, object]:
    row: dict[str, object] = {"cell_type": kind,
        "id": hashlib.sha256(source.encode()).hexdigest()[:8], "metadata": {},
        "source": source.splitlines(keepends=True)}
    if kind == "code":
        row.update({"execution_count": None, "outputs": []})
    return row


def build(seed: int) -> dict[str, object]:
    """Return one notebook restricted to a single frozen seed."""
    output_name = "aether-core02-results" if seed == 11 else f"aether-core02-seed{seed}"
    cells = [
        _cell("markdown", f"""# AETHER CORE-02 parallel shard: seed {seed}

This notebook runs **only seed {seed}**, but runs all five frozen methods in the
required order. It never accesses development-audit, validation or test.

Internet must be enabled. A CPU runtime is sufficient and is the frozen
configuration. If interrupted, save the checkpoint tar from `/kaggle/working`,
attach it to a new notebook session as a Kaggle dataset, and run all cells again.
Do not attach another seed's checkpoint.
"""),
        _cell("code", f"""from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,tarfile
SEED={seed}; WORK=Path('/kaggle/working'); RUNTIME=Path('/tmp/aether-core02-seed{seed}')
REPO=RUNTIME/'aether'; VENV=RUNTIME/'venv'; PY=VENV/'bin'/'python'; CACHE=RUNTIME/'hf-cache'
OUTPUT=WORK/{output_name!r}; COMMIT={COMMIT!r}; URL='https://github.com/ama1a005/aether.git'
os.environ.update({{'MPLBACKEND':'Agg','PYTHONNOUSERSITE':'1','TOKENIZERS_PARALLELISM':'false','OMP_NUM_THREADS':'2','MKL_NUM_THREADS':'2'}})
for path in (RUNTIME,CACHE): path.mkdir(parents=True,exist_ok=True)
print('Shard seed:',SEED,'host Python:',sys.version)
"""),
        _cell("code", f"""# Restore at most one checkpoint. Seed 11 also accepts the original campaign name.
patterns=['aether-core02-seed{seed}-checkpoint.tar.gz']
if SEED==11: patterns.append('aether-core02-checkpoint.tar.gz')
checkpoints=[]
for pattern in patterns: checkpoints += list(Path('/kaggle/input').rglob(pattern))
checkpoints += [p for pattern in patterns for p in [WORK/pattern] if p.is_file()]
checkpoints=list(dict.fromkeys(checkpoints))
if len(checkpoints)>1: raise RuntimeError(f'Attach exactly zero or one seed {{SEED}} checkpoint: {{checkpoints}}')
if checkpoints:
 with tarfile.open(checkpoints[0],'r:gz') as bundle:
  members=bundle.getmembers(); roots={{Path(m.name).parts[0] for m in members if Path(m.name).parts}}
  allowed={{'aether-core02-seed{seed}'}} | ({{'aether-core02-results'}} if SEED==11 else set())
  if len(roots)!=1 or not roots.issubset(allowed): raise ValueError(f'foreign checkpoint root: {{roots}}')
  for member in members:
   if Path(member.name).is_absolute() or '..' in Path(member.name).parts or member.issym() or member.islnk(): raise ValueError(member.name)
  bundle.extractall(WORK,filter='data')
 extracted=WORK/next(iter(roots)); OUTPUT=extracted
 print('Restored checkpoint:',checkpoints[0],'to',OUTPUT)
else: print('Fresh seed',SEED,'shard at',OUTPUT)
"""),
        _cell("code", """# Install isolated Python 3.11 and checkout the immutable approved source.
if shutil.which('uv') is None: subprocess.run([sys.executable,'-m','pip','install','uv'],check=True)
UV=shutil.which('uv'); env=os.environ.copy(); env['UV_PYTHON_INSTALL_DIR']=str(RUNTIME/'uv-python')
if not PY.exists(): subprocess.run([UV,'venv','--python','3.11.9',str(VENV)],check=True,env=env)
if not REPO.exists(): subprocess.run(['git','clone','--branch','lm','--single-branch',URL,str(REPO)],check=True)
subprocess.run(['git','fetch','--no-tags','origin','lm'],cwd=REPO,check=True)
subprocess.run(['git','checkout','--detach',COMMIT],cwd=REPO,check=True)
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()==COMMIT
assert not subprocess.check_output(['git','status','--porcelain'],cwd=REPO,text=True).strip()
lock=WORK/f'core02-seed{SEED}-lock.txt'; lines=(REPO/'requirements-lock.txt').read_text().splitlines()
lock.write_text(chr(10).join(x for x in lines if not x.startswith('torch=='))+chr(10))
subprocess.run([UV,'pip','install','--python',str(PY),'torch==2.14.1','--index-url','https://download.pytorch.org/whl/cpu'],check=True,env=env)
subprocess.run([UV,'pip','install','--python',str(PY),'-r',str(lock)],check=True,env=env)
subprocess.run([UV,'pip','install','--python',str(PY),'--no-deps','-e',str(REPO)],check=True,env=env)
subprocess.run([str(PY),'-m','pytest','tests/unit/test_qci2_parallel_shards.py','tests/unit/test_phase1_core_matched_search.py','tests/unit/test_phase1_core_qwen_evaluator.py','tests/unit/test_model_adapter.py','-q'],cwd=REPO,check=True)
print(subprocess.check_output([str(PY),'-c','import sys; print(sys.version); assert sys.version_info[:2]==(3,11)'],text=True))
"""),
        _cell("code", """# Download the immutable Qwen snapshot (one worker avoids RAM/network spikes).
revision='989aa7980e4cf806f80c7fef2b1adb7bc71aa306'
code="from huggingface_hub import snapshot_download; print(snapshot_download('Qwen/Qwen2.5-1.5B-Instruct',revision='"+revision+"',cache_dir=r'"+str(CACHE)+"',max_workers=1))"
snapshot=Path(subprocess.check_output([str(PY),'-c',code],text=True).strip())
assert snapshot.name==revision
print('Snapshot ready:',snapshot)
"""),
        _cell("code", """# Model-free preflight. Existing checkpoints must already contain its passing record.
if not OUTPUT.exists():
 import yaml
 proposal=yaml.safe_load((REPO/'configs/phase1_core/qci2_method_freeze_v2.yaml').read_text())
 inputs=[]
 for record in proposal['evidence_inputs'].values(): inputs += ['--input-artifact',str(REPO/record['path'])]
 command=[str(PY),'-m','experiments.phase1.qci2_matched_search','--preflight-only','--model-snapshot',str(snapshot),'--declared-budget','7360','--output',str(OUTPUT),'--seed',str(SEED),*inputs]
 subprocess.run(command,cwd=REPO,check=True)
else:
 preflight=json.loads((OUTPUT/'preflight.json').read_text())
 assert preflight['overall']=='PASS' and preflight['model_accessed'] is False
 print('Using restored passing preflight')
"""),
        _cell("code", """# Execute/resume and stream progress. Every completed mask refreshes the checkpoint tar.
command=[str(PY),'-u','-m','instrumentation.run_qci2_matched_search','--output',str(OUTPUT),'--model-snapshot',str(snapshot),'--resume','--seed',str(SEED)]
process=subprocess.Popen(command,cwd=REPO,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
assert process.stdout is not None
for line in process.stdout: print(line,end='',flush=True)
code=process.wait()
if code: raise subprocess.CalledProcessError(code,command)
"""),
        _cell("code", f"""# Independently verify, then export the final seed shard.
subprocess.run([str(PY),'-m','scripts.verify_qci2_matched_search_shard',str(OUTPUT)],cwd=REPO,check=True)
archive=WORK/'aether-core02-seed{seed}-results.tar.gz'
with tarfile.open(archive,'w:gz') as bundle: bundle.add(OUTPUT,arcname=OUTPUT.name)
print('FINAL SHARD',archive)
print('SHA256',hashlib.sha256(archive.read_bytes()).hexdigest())
print('Download this final shard. It is not the merged 15-run evidence bundle.')
"""),
    ]
    return {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3",
        "language": "python", "name": "python3"}}, "nbformat": 4, "nbformat_minor": 5}


def main() -> None:
    for seed in (11, 22, 33):
        output = ROOT / f"notebooks/aether_qwen_core02_seed{seed}.ipynb"
        output.write_text(json.dumps(build(seed), indent=1) + "\n", encoding="utf-8")
        print(output)


if __name__ == "__main__":
    main()
