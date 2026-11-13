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
    snapshot = "--snapshot-manifest /kaggle/working/model_snapshot_manifest.json" if benchmark == "bfcl" else ""
    package = "bfcl_eval==2026.3.23" if benchmark == "bfcl" else "agentdojo==0.1.35"
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
subprocess.run(['git','clone','--branch','phase1/core-nov19','--single-branch',URL,str(REPO)],check=True)
subprocess.run(['git','fetch','origin',COMMIT],cwd=REPO,check=True)
subprocess.run(['git','checkout','--detach',COMMIT],cwd=REPO,check=True)
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()==COMMIT
assert not subprocess.check_output(['git','status','--porcelain'],cwd=REPO,text=True).strip()
"""),
        _cell("code", f"""subprocess.run([UV,'pip','install','--python',str(PY),'-r',str(REPO/'requirements-lock.txt')],check=True,env=env)
subprocess.run([UV,'pip','install','--python',str(PY),{package!r}],check=True,env=env)
subprocess.run([UV,'pip','install','--python',str(PY),'--no-deps','-e',str(REPO)],check=True,env=env)
subprocess.run([str(PY),'-m','pytest','tests/unit/test_external_bundle.py','tests/unit/test_native_benchmark_runners.py','tests/unit/test_native_official_package.py','-q'],cwd=REPO,check=True)
"""),
        _cell("code", f"""command=[str(PY),'-m','benchmarks.run_native_official',{benchmark!r},'--output',str(OUTPUT)]
{("command += ['--snapshot-manifest','/kaggle/working/model_snapshot_manifest.json']" if snapshot else "")}
subprocess.run(command,cwd=REPO,check=True)
subprocess.run([str(PY),'-m','scripts.verify_external_bundle',str(OUTPUT),'--expected-kind',{(benchmark + '_official')!r}],cwd=REPO,check=True)
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
