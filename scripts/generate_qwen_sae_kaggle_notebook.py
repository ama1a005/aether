"""Generate the commit-pinned dual-T4 Qwen SAE Kaggle notebook."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _code(source: str) -> dict:
    return {"cell_type": "code", "execution_count": None, "metadata": {},
            "outputs": [], "source": [line + "\n" for line in source.splitlines()]}


def _markdown(source: str) -> dict:
    return {"cell_type": "markdown", "metadata": {},
            "source": [line + "\n" for line in source.splitlines()]}


def generate(commit: str, destination: Path) -> None:
    """Write a restart-safe notebook pinned to an immutable implementation commit."""
    cells = [
        _markdown("""# AETHER Qwen SAE v1.2 - dual-T4 execution

Use a Kaggle **2 x T4 GPU** session with Internet enabled. This v1.2 package
verifies the exact approved corpus file before model work. Add notebook secrets
`HF_TOKEN` (write token) and `AETHER_HF_REPO` (for example
`DXVNX05/aether-qwen-sae-v1-2`). The dataset repository is created privately.

Run all cells in order. Completed corpus blocks and epoch checkpoints are
uploaded continuously. If Kaggle stops, start a new session with the same two
secrets and rerun all cells; retained work is restored automatically.

This is development-only reconstruction/sparsity evidence. It does not access
validation/test cases and cannot support a causal SAE-feature claim."""),
        _code(f"""from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,tarfile,threading,time
WORK=Path('/kaggle/working'); RUNTIME=Path('/tmp/aether-sae-v1-2')
REPO=RUNTIME/'aether'; VENV=RUNTIME/'venv'; PY=VENV/'bin'/'python'
CACHE=RUNTIME/'hf-cache'; OUTPUT=WORK/'aether-qwen-sae-v1-2'
URL='https://github.com/ama1a005/aether.git'; COMMIT='{commit}'
REMOTE_PREFIX='sae-v1-2'
os.environ.update({{'MPLBACKEND':'Agg','PYTHONNOUSERSITE':'1','TOKENIZERS_PARALLELISM':'false'}})
for path in (RUNTIME,CACHE,OUTPUT): path.mkdir(parents=True,exist_ok=True)
print(subprocess.run(['nvidia-smi','--query-gpu=index,name,memory.total,memory.free','--format=csv,noheader'],capture_output=True,text=True).stdout)
assert len([line for line in subprocess.run(['nvidia-smi','--query-gpu=index','--format=csv,noheader'],capture_output=True,text=True).stdout.splitlines() if line.strip()])>=2"""),
        _code("""# Isolated Python 3.11 and immutable source.
if shutil.which('uv') is None: subprocess.run([sys.executable,'-m','pip','install','uv'],check=True)
UV=shutil.which('uv'); env=os.environ.copy(); env['UV_PYTHON_INSTALL_DIR']=str(RUNTIME/'uv-python')
if not PY.exists(): subprocess.run([UV,'venv','--python','3.11.9',str(VENV)],check=True,env=env)
if not REPO.exists(): subprocess.run(['git','clone','--branch','m3/mech-interventions','--single-branch',URL,str(REPO)],check=True)
subprocess.run(['git','fetch','--no-tags','origin','m3/mech-interventions'],cwd=REPO,check=True)
subprocess.run(['git','checkout','--detach',COMMIT],cwd=REPO,check=True)
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()==COMMIT
assert not subprocess.check_output(['git','status','--porcelain'],cwd=REPO,text=True).strip()
lock=WORK/'sae-lock.txt'; lines=(REPO/'requirements-lock.txt').read_text().splitlines()
lock.write_text(chr(10).join(x for x in lines if not x.startswith('torch=='))+chr(10))
subprocess.run([UV,'pip','install','--python',str(PY),'torch==2.14.1','--index-url','https://download.pytorch.org/whl/cu130'],check=True,env=env)
subprocess.run([UV,'pip','install','--python',str(PY),'-r',str(lock)],check=True,env=env)
subprocess.run([UV,'pip','install','--python',str(PY),'pyarrow==22.0.0'],check=True,env=env)
subprocess.run([UV,'pip','install','--python',str(PY),'--no-deps','-e',str(REPO)],check=True,env=env)
subprocess.run([str(PY),'-m','pytest','tests/unit/test_qwen_sae_training_package.py','tests/unit/test_sae_training_freeze.py','tests/unit/test_sae_checkpoint.py','-q'],cwd=REPO,check=True)
subprocess.run([str(PY),'-c','import torch; assert torch.cuda.device_count()>=2; print(torch.__version__,torch.version.cuda,torch.cuda.get_device_name(0),torch.cuda.get_device_name(1))'],check=True)"""),
        _code("""# Private durable storage: restore every previously uploaded file.
from kaggle_secrets import UserSecretsClient
from huggingface_hub import HfApi,snapshot_download
secrets=UserSecretsClient(); os.environ['HF_TOKEN']=secrets.get_secret('HF_TOKEN')
HF_REPO=secrets.get_secret('AETHER_HF_REPO'); assert os.environ['HF_TOKEN'] and HF_REPO
api=HfApi(token=os.environ['HF_TOKEN'])
api.create_repo(repo_id=HF_REPO,repo_type='dataset',private=True,exist_ok=True)
assert api.repo_info(repo_id=HF_REPO,repo_type='dataset').private
try:
 remote=Path(snapshot_download(HF_REPO,repo_type='dataset',allow_patterns=f'{REMOTE_PREFIX}/*',cache_dir=RUNTIME/'remote-cache'))/REMOTE_PREFIX
 if remote.is_dir(): shutil.copytree(remote,OUTPUT,dirs_exist_ok=True); print('Restored remote checkpoint:',remote)
except Exception as error:
 print('No prior remote checkpoint restored:',type(error).__name__,str(error))

def upload_tree_once(root, remote_prefix):
 root=Path(root)
 if not root.is_dir(): raise FileNotFoundError(root)
 if not any(path.is_file() for path in root.rglob('*')): return
 api.upload_folder(folder_path=str(root),path_in_repo=remote_prefix,repo_id=HF_REPO,
                   repo_type='dataset',commit_message=f'checkpoint batch: {remote_prefix}')

def run_with_sync(commands, watched, label):
 stop=threading.Event(); uploaded={}; sync_errors=[]
 def fingerprint(root):
  return tuple((path.relative_to(root).as_posix(),path.stat().st_size,path.stat().st_mtime_ns)
               for path in sorted(Path(root).rglob('*')) if path.is_file())
 def sync():
  while not stop.wait(60):
   try:
    for root,remote in watched:
     stamp=fingerprint(root)
     if stamp and uploaded.get(str(root))!=stamp:
      upload_tree_once(root,remote); uploaded[str(root)]=stamp
   except BaseException as error:
    sync_errors.append(error); stop.set(); return
 thread=threading.Thread(target=sync,daemon=True); thread.start()
 processes=[subprocess.Popen(command,cwd=REPO,env=os.environ.copy()) for command in commands]
 codes=[process.wait() for process in processes]; stop.set(); thread.join(timeout=10)
 for root,remote in watched: upload_tree_once(root,remote)
 if sync_errors: raise RuntimeError(f'{label} background checkpoint upload failed') from sync_errors[0]
 if any(codes): raise RuntimeError(f'{label} failed with exit codes {codes}')"""),
        _code("""# Download pinned model and corpus snapshots, then create exact token IDs.
from huggingface_hub import hf_hub_download,snapshot_download
MODEL_ID='Qwen/Qwen2.5-1.5B-Instruct'; MODEL_REV='989aa7980e4cf806f80c7fef2b1adb7bc71aa306'
DATA_ID='Salesforce/wikitext'; DATA_REV='b08601e04326c79dfdd32d625aee71d232d685c3'
DATA_FILE='wikitext-2-raw-v1/train-00000-of-00001.parquet'
DATA_SHA256='e83889baabc497075506f91975be5fac0d45c5290b6b20582c8cd1e853d0c9f7'
data_file=Path(hf_hub_download(repo_id=DATA_ID,repo_type='dataset',revision=DATA_REV,
 filename=DATA_FILE,cache_dir=CACHE))
assert data_file.name=='train-00000-of-00001.parquet'
observed_data_hash=hashlib.sha256(data_file.read_bytes()).hexdigest()
assert observed_data_hash==DATA_SHA256,f'WikiText parquet SHA-256 mismatch: {observed_data_hash}'
model_snapshot=Path(snapshot_download(MODEL_ID,revision=MODEL_REV,cache_dir=CACHE,max_workers=2))
assert model_snapshot.name==MODEL_REV
corpus=OUTPUT/'corpus'
if not (corpus/'corpus_source_manifest.json').is_file():
 token_code=r'''import sys
from pathlib import Path
import pandas as pd
from transformers import AutoTokenizer
from experiments.phase1.qwen_sae_training import write_token_artifacts
model_snapshot,data_file,corpus=map(Path,sys.argv[1:])
if not data_file.is_file(): raise FileNotFoundError('pinned WikiText training parquet is absent')
files=[data_file]
texts=[]
for file in files: texts.extend(pd.read_parquet(file,columns=['text'])['text'].tolist())
tokenizer=AutoTokenizer.from_pretrained(model_snapshot,local_files_only=True,trust_remote_code=False)
write_token_artifacts(texts,tokenizer,corpus,files)
'''
 subprocess.run([str(PY),'-c',token_code,str(model_snapshot),str(data_file),str(corpus)],cwd=REPO,check=True)
upload_tree_once(corpus,f'{REMOTE_PREFIX}/corpus')
print(json.loads((corpus/'corpus_source_manifest.json').read_text())['selected_token_count'])"""),
        _code("""# Dual-T4 corpus capture. Reruns skip every verified existing block.
activations=OUTPUT/'activations'; activations.mkdir(exist_ok=True)
commands=[]
for gpu in (0,1):
 commands.append([str(PY),'-u','-m','experiments.phase1.qwen_sae_training','capture-corpus',
  '--tokens',str(corpus/'corpus_token_ids.npy'),'--output',str(activations),
  '--snapshot',str(model_snapshot),'--cache',str(CACHE),'--shard-index',str(gpu),
  '--shard-count','2','--device',f'cuda:{gpu}'])
run_with_sync(commands,[(activations,f'{REMOTE_PREFIX}/activations')],'dual-GPU activation capture')
assert len(list(activations.glob('block_*.npy')))==256
print('All 256 activation blocks retained.')"""),
        _code("""# Three frozen SAE seeds. Seeds 11/22 run together, then seed 33.
seeds_root=OUTPUT/'seeds'; seeds_root.mkdir(exist_ok=True)
def train_command(seed,gpu):
 return [str(PY),'-u','-m','experiments.phase1.qwen_sae_training','train-seed',
  '--activations',str(activations),'--output',str(seeds_root/f'seed-{seed}'),
  '--seed',str(seed),'--device',f'cuda:{gpu}']
run_with_sync([train_command(11,0),train_command(22,1)],[(seeds_root,f'{REMOTE_PREFIX}/seeds')],'SAE seeds 11 and 22')
run_with_sync([train_command(33,0)],[(seeds_root,f'{REMOTE_PREFIX}/seeds')],'SAE seed 33')
assert all((seeds_root/f'seed-{seed}'/'seed_summary.json').is_file() for seed in (11,22,33))
print('All frozen seeds complete.')"""),
        _code("""# Select without AETHER audit access, then capture the frozen audit on GPU 0.
selection_code='from pathlib import Path; from experiments.phase1.qwen_sae_training import select_seed; print(select_seed(Path(__import__("sys").argv[1])))'
selected=Path(subprocess.check_output([str(PY),'-c',selection_code,str(seeds_root)],cwd=REPO,text=True).strip())
print('Selected checkpoint:',selected)
audit=OUTPUT/'audit'
if not (audit/'aether_audit_activation_manifest.json').is_file():
 subprocess.run([str(PY),'-u','-m','experiments.phase1.qwen_sae_training','capture-audit',
  '--output',str(audit),'--snapshot',str(model_snapshot),'--cache',str(CACHE),'--device','cuda:0'],cwd=REPO,check=True)
upload_tree_once(audit,f'{REMOTE_PREFIX}/audit')"""),
        _code("""# Final evaluation, independent verification, durable export.
final=OUTPUT/'final'
if not (final/'summary.json').is_file():
 subprocess.run([str(PY),'-m','experiments.phase1.qwen_sae_training','evaluate-audit',
  '--seeds',str(seeds_root),'--audit',str(audit),'--output',str(final)],cwd=REPO,check=True)
verification=subprocess.check_output([str(PY),'-m','scripts.verify_qwen_sae_bundle',str(OUTPUT)],cwd=REPO,text=True)
print(verification); upload_tree_once(OUTPUT,REMOTE_PREFIX)
archive=WORK/'aether-qwen-sae-v1-2-results.tar.gz'
with tarfile.open(archive,'w:gz') as bundle: bundle.add(OUTPUT,arcname=OUTPUT.name)
api.upload_file(path_or_fileobj=str(archive),path_in_repo=f'{REMOTE_PREFIX}/aether-qwen-sae-v1-2-results.tar.gz',repo_id=HF_REPO,repo_type='dataset')
print(json.dumps(json.loads((final/'summary.json').read_text()),indent=2)); print('ARCHIVE:',archive,archive.stat().st_size)"""),
    ]
    notebook = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                                                "language_info": {"name": "python", "version": "3.13"}},
                "nbformat": 4, "nbformat_minor": 5}
    destination.write_text(json.dumps(notebook, indent=1), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(); generate(args.commit, args.output)


if __name__ == "__main__":
    main()
