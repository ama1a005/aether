"""Build commit-pinned notebooks for Qwen red-team, Agent-C or SAE execution."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re


def _cell(kind: str, source: str) -> dict[str, object]:
    row: dict[str, object] = {"cell_type": kind, "id": hashlib.sha256(source.encode()).hexdigest()[:8],
                              "metadata": {}, "source": source.splitlines(keepends=True)}
    if kind == "code": row.update({"execution_count": None, "outputs": []})
    return row


def build(kind: str, commit: str) -> dict[str, object]:
    """Return one clean immutable-source supporting-experiment notebook."""
    if kind not in {"red_team", "agent_c", "sae"} or re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        raise ValueError("kind and immutable 40-hex commit are required")
    setup = f"""from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,tarfile
WORK=Path('/kaggle/working'); RUNTIME=Path('/tmp/aether-{kind}'); REPO=RUNTIME/'aether'
VENV=RUNTIME/'venv'; PY=VENV/'bin'/'python'; OUTPUT=WORK/'aether-{kind}-results'
COMMIT={commit!r}; URL='https://github.com/ama1a005/aether.git'
RUNTIME.mkdir(parents=True,exist_ok=True); os.environ['PYTHONNOUSERSITE']='1'
if shutil.which('uv') is None: subprocess.run([sys.executable,'-m','pip','install','uv'],check=True)
UV=shutil.which('uv'); env=os.environ.copy(); env['UV_PYTHON_INSTALL_DIR']=str(RUNTIME/'uv-python')
subprocess.run([UV,'venv','--python','3.11.9',str(VENV)],check=True,env=env)
subprocess.run(['git','clone','--branch','phase1/core-nov19','--single-branch',URL,str(REPO)],check=True)
subprocess.run(['git','fetch','origin',COMMIT],cwd=REPO,check=True)
subprocess.run(['git','checkout','--detach',COMMIT],cwd=REPO,check=True)
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()==COMMIT
subprocess.run([UV,'pip','install','--python',str(PY),'-r',str(REPO/'requirements-lock.txt')],check=True,env=env)
subprocess.run([UV,'pip','install','--python',str(PY),'--no-deps','-e',str(REPO)],check=True,env=env)
"""
    if kind == "agent_c":
        execution = """subprocess.run([str(PY),'-m','experiments.phase1.qwen_agent_c','--config',str(REPO/'configs/experiments/agent_c_qwen_development.yaml'),'--output',str(OUTPUT)],cwd=REPO,check=True)"""
    elif kind == "sae":
        execution = """metadata=list(Path('/kaggle/input').rglob('metadata.json')); weights=list(Path('/kaggle/input').rglob('weights.npz')); activations=list(Path('/kaggle/input').rglob('activations.pt'))
assert len(metadata)==len(weights)==len(activations)==1,'Attach exactly one reviewed SAE checkpoint and activation artifact'
config=REPO/'configs/experiments/qwen_sae_development.yaml'
payload=__import__('yaml').safe_load(config.read_text()); payload['checkpoint_path']=str(metadata[0].parent); payload['activation_path']=str(activations[0])
runtime=WORK/'qwen-sae-runtime.yaml'; runtime.write_text(__import__('yaml').safe_dump(payload))
subprocess.run([str(PY),'-m','experiments.phase1.qwen_sae_evaluation','--config',str(runtime),'--output',str(OUTPUT)],cwd=REPO,check=True)"""
    else:
        execution = """from huggingface_hub import snapshot_download
revision='989aa7980e4cf806f80c7fef2b1adb7bc71aa306'; cache=RUNTIME/'hf-cache'
snapshot=Path(snapshot_download('Qwen/Qwen2.5-1.5B-Instruct',revision=revision,cache_dir=cache,max_workers=1))
files=[]
for path in sorted(p for p in snapshot.rglob('*') if p.is_file()): files.append({'path':path.relative_to(snapshot).as_posix(),'size':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
manifest=WORK/'model_snapshot_manifest.json'; manifest.write_text(json.dumps({'model_id':'Qwen/Qwen2.5-1.5B-Instruct','resolved_revision':revision,'snapshot_path':str(snapshot),'files':files},indent=2))
subprocess.run([str(PY),'-m','experiments.phase1.qwen_red_team','--config',str(REPO/'configs/experiments/qwen_red_team_development.yaml'),'--snapshot-manifest',str(manifest),'--output',str(OUTPUT)],cwd=REPO,check=True)"""
    archive = f"""subprocess.run([str(PY),'-m','scripts.verify_external_bundle',str(OUTPUT)],cwd=REPO,check=True)
archive=WORK/'aether-{kind}-results.tar.gz'
with tarfile.open(archive,'w:gz') as bundle: bundle.add(OUTPUT,arcname=OUTPUT.name)
print(archive,hashlib.sha256(archive.read_bytes()).hexdigest())"""
    cells = [_cell("markdown", f"# AETHER {kind} supporting execution\n\nDevelopment-only; requires reviewed committed config."),
             _cell("code", setup), _cell("code", execution), _cell("code", archive)]
    return {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}}, "nbformat": 4, "nbformat_minor": 5}


def main() -> None:
    """Write the selected supporting notebook."""
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=("red_team", "agent_c", "sae")); parser.add_argument("--commit", required=True)
    parser.add_argument("--output", type=Path, required=True); arguments = parser.parse_args()
    arguments.output.write_text(json.dumps(build(arguments.kind, arguments.commit), indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__": main()
