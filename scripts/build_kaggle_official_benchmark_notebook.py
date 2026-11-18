"""Build a commit-pinned Kaggle notebook for BFCL or AgentDojo native execution."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def _cell(kind: str, source: str) -> dict[str, object]:
    row: dict[str, object] = {"cell_type": kind, "id": hashlib.sha256(source.encode()).hexdigest()[:8],
                              "metadata": {}, "source": source.splitlines(keepends=True)}
    if kind == "code":
        row.update({"execution_count": None, "outputs": []})
    return row


def build(benchmark: str, commit: str) -> dict[str, object]:
    """Return a clean notebook pinned to one source commit and benchmark."""
    if benchmark not in {"bfcl", "agentdojo"}:
        raise ValueError("benchmark must be bfcl or agentdojo")
    if re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        raise ValueError("notebook requires an immutable 40-hex source commit")
    if benchmark == "bfcl":
        package_setup = """import hashlib
WHEELHOUSE=RUNTIME/'wheelhouse'; WHEELHOUSE.mkdir(parents=True,exist_ok=True)
subprocess.run([str(PY),'-m','pip','download','--no-deps','--only-binary=:all:','--dest',str(WHEELHOUSE),'bfcl_eval==2026.3.23'],check=True)
WHEELS=sorted(WHEELHOUSE.glob('bfcl_eval-2026.3.23-*.whl'))
assert len(WHEELS)==1, f'Expected exactly one pinned BFCL wheel, found {len(WHEELS)}'
WHEEL=WHEELS[0]; WHEEL_SHA256=hashlib.sha256(WHEEL.read_bytes()).hexdigest()
assert WHEEL_SHA256=='3bb6dfa5f0c68ad403c9ec50b00db2bb3b4cc9b38ab1ff33f48fe30d853d3a0a', WHEEL_SHA256
subprocess.run([str(PY),'-m','pip','install',str(WHEEL)],check=True)
"""
        snapshot_setup = """from huggingface_hub import snapshot_download
from benchmarks.run_native_official import _load_config
from benchmarks.nov19_bfcl.preflight import check_backend_and_hardware, check_package
from causal.remediation_freeze import frozen_text_hash_matches
CONFIG=REPO/'configs/benchmarks/phase1_external.yaml'
_load_config(CONFIG,'bfcl')
wheel_ok,wheel_reasons,_=check_package(wheel_path=WHEEL)
gpu_ok,gpu_reasons,gpu_details=check_backend_and_hardware('vllm',1)
assert wheel_ok, wheel_reasons
assert gpu_ok, {'reasons':gpu_reasons,'details':gpu_details}
FROZEN_MANIFEST=REPO/'results/phase1/model_qualification/qwen15b_kaggle_20261110/model_snapshot_manifest.json'
assert frozen_text_hash_matches(FROZEN_MANIFEST,'1b282b730f38fbe992608e8837fe0f619463a767f93e08d97cd0950d55644f11')
frozen=json.loads(FROZEN_MANIFEST.read_text(encoding='utf-8'))
REVISION='989aa7980e4cf806f80c7fef2b1adb7bc71aa306'
snapshot=Path(snapshot_download('Qwen/Qwen2.5-1.5B-Instruct',revision=REVISION,cache_dir=RUNTIME/'hf-cache',max_workers=1))
expected={item['path']:(item['size'],item['sha256']) for item in frozen['files']}
observed={p.relative_to(snapshot).as_posix():(p.stat().st_size,hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(snapshot.rglob('*')) if p.is_file()}
assert observed==expected, 'Downloaded snapshot differs from the independently retained qualification manifest'
SNAPSHOT_MANIFEST=WORK/'model_snapshot_manifest.json'
SNAPSHOT_MANIFEST.write_text(json.dumps({'model_id':'Qwen/Qwen2.5-1.5B-Instruct','resolved_revision':REVISION,'tokenizer_revision':REVISION,'snapshot_path':str(snapshot),'files':[{'path':name,'size':size,'sha256':digest} for name,(size,digest) in sorted(observed.items())]},indent=2),encoding='utf-8')
"""
        benchmark_verification = "subprocess.run([str(PY),'-m','scripts.verify_bfcl_bundle',str(OUTPUT)],cwd=REPO,check=True)"
    else:
        package_setup = "subprocess.run([UV,'pip','install','--python',str(PY),'agentdojo==0.1.35'],check=True,env=env)\n"
        snapshot_setup = ""
        benchmark_verification = ""
    cells = [
        _cell("markdown", f"""# AETHER {benchmark.upper()} official execution

Runs the pinned native official package on development-scoped preparation only.
This notebook does not access AETHER validation/test splits. It exports raw
official outputs plus a hash-verified AETHER wrapper bundle.
"""),
        _cell("code", f"""from pathlib import Path
import os,shutil,subprocess,sys,tarfile,hashlib
WORK=Path('/kaggle/working'); RUNTIME=Path('/tmp/aether-{benchmark}')
REPO=RUNTIME/'aether'; VENV=RUNTIME/'venv'; PY=VENV/'bin'/'python'
OUTPUT=WORK/'aether-{benchmark}-official'; COMMIT={commit!r}
URL='https://github.com/ama1a005/aether.git'
os.environ.update({{'PYTHONNOUSERSITE':'1','MPLBACKEND':'Agg'}})
RUNTIME.mkdir(parents=True,exist_ok=True)
"""),
        _cell("code", """if shutil.which('uv') is None: subprocess.run([sys.executable,'-m','pip','install','uv'],check=True)
UV=shutil.which('uv'); env=os.environ.copy(); env['UV_PYTHON_INSTALL_DIR']=str(RUNTIME/'uv-python')
subprocess.run([UV,'venv','--python','3.11.9',str(VENV)],check=True,env=env)
subprocess.run(['git','clone','--branch','lm','--single-branch',URL,str(REPO)],check=True)
subprocess.run(['git','fetch','origin',COMMIT],cwd=REPO,check=True)
subprocess.run(['git','checkout','--detach',COMMIT],cwd=REPO,check=True)
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()==COMMIT
assert not subprocess.check_output(['git','status','--porcelain'],cwd=REPO,text=True).strip()
"""),
        _cell("code", f"""subprocess.run([UV,'pip','install','--python',str(PY),'-r',str(REPO/'requirements-lock.txt')],check=True,env=env)
{package_setup}
subprocess.run([UV,'pip','install','--python',str(PY),'--no-deps','-e',str(REPO)],check=True,env=env)
subprocess.run([str(PY),'-m','pytest','tests/unit/test_external_bundle.py','tests/unit/test_native_benchmark_runners.py','tests/unit/test_native_official_package.py','-q'],cwd=REPO,check=True)
"""),
        *([_cell("code", snapshot_setup)] if snapshot_setup else []),
        _cell("code", f"""command=[str(PY),'-m','benchmarks.run_native_official',{benchmark!r},'--config',str(REPO/'configs/benchmarks/phase1_external.yaml'),'--output',str(OUTPUT)]
{("command += ['--snapshot-manifest',str(SNAPSHOT_MANIFEST),'--package-wheel',str(WHEEL),'--backend','vllm','--num-gpus','1']" if benchmark == 'bfcl' else "")}
subprocess.run(command,cwd=REPO,check=True)
subprocess.run([str(PY),'-m','scripts.verify_external_bundle',str(OUTPUT),'--expected-kind',{(benchmark + '_official')!r}],cwd=REPO,check=True)
{benchmark_verification}
archive=WORK/'aether-{benchmark}-official-results.tar.gz'
with tarfile.open(archive,'w:gz') as bundle: bundle.add(OUTPUT,arcname=OUTPUT.name)
print(archive,hashlib.sha256(archive.read_bytes()).hexdigest())
"""),
    ]
    return {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}}, "nbformat": 4, "nbformat_minor": 5}


def main() -> None:
    """Write a selected official-benchmark notebook."""
    parser = argparse.ArgumentParser()
    parser.add_argument("benchmark", choices=("bfcl", "agentdojo"))
    parser.add_argument("--commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    arguments.output.write_text(json.dumps(build(arguments.benchmark, arguments.commit), indent=1) + "\n", encoding="utf-8")
    print(arguments.output)


if __name__ == "__main__":
    main()
