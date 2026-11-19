"""Build the commit-pinned, restart-safe CORE-05 Kaggle notebook."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.build_kaggle_core04_notebook import build as build_core04


ROOT = Path(__file__).resolve().parents[1]
COMMIT = "c2a4ff24c1789bfe9db9b220e728e4443a0c1133"
CORE04_COMMIT = "950961d77651ae965fd7b1feb957023d926b5729"


def build() -> dict[str, object]:
    """Return the complete once-only CORE-05 notebook."""
    notebook = build_core04()
    replacements = (
        (CORE04_COMMIT, COMMIT),
        ("CORE-04", "CORE-05"), ("core04", "core05"),
        ("aether-core04", "aether-core05"),
        ("tests/unit/test_core05_locked_validation_freeze.py", "tests/unit/test_core05_once_only_test_freeze.py"),
        ("tests/unit/test_core05_execution_package.py", "tests/unit/test_core05_execution_package.py"),
        ("experiments.phase1.core05_locked_validation", "experiments.phase1.core05_once_only_test"),
        ("scripts.verify_core05_validation_bundle", "scripts.verify_core05_test_bundle"),
    )
    for cell in notebook["cells"]:
        source = "".join(cell["source"])
        for old, new in replacements:
            source = source.replace(old, new)
        cell["source"] = source.splitlines(keepends=True)
    notebook["cells"][0]["source"] = """# AETHER CORE-05 once-only held-out test

This notebook performs the one approved test attempt on eight locked test
cases. It writes an attempt marker before model access, checkpoints every
completed arm/seed unit, and may resume only that same attempt. Never delete
the private checkpoint dataset or start another notebook after completion.

Use a standard Kaggle CPU runtime with Internet enabled. Add secrets `HF_TOKEN`
and `AETHER_HF_REPO` (recommended value: `DXVNX05/aether-core05`). The paired
clean activation donor remains oracle information, so even a positive result
is not an oracle-free deployable defense.
""".splitlines(keepends=True)
    before_access = """# Write/restore the attempt marker before any model repository access.
revision='989aa7980e4cf806f80c7fef2b1adb7bc71aa306'
snapshot=CACHE/'models--Qwen--Qwen2.5-1.5B-Instruct'/'snapshots'/revision
if not OUTPUT.exists():
 subprocess.run([str(PY),'-m','experiments.phase1.core05_once_only_test','--preflight-only',
                 '--output',str(OUTPUT),'--model-snapshot',str(snapshot)],cwd=REPO,check=True)
else:
 gate=json.loads((OUTPUT/'preflight.json').read_text())
 marker=json.loads((OUTPUT/'attempt_marker.json').read_text())
 assert gate['overall']=='PASS' and gate['model_accessed'] is False
 assert marker['proposal_sha256']==gate['proposal_sha256']
 print('Restored attempt',marker['attempt_id'],'at commit',gate['git_commit'])
"""
    download = """# Only after the attempt exists, download/reuse the immutable snapshot.
code="from huggingface_hub import snapshot_download; print(snapshot_download('Qwen/Qwen2.5-1.5B-Instruct',revision='"+revision+"',cache_dir=r'"+str(CACHE)+"',max_workers=1))"
resolved=Path(subprocess.check_output([str(PY),'-c',code],text=True).strip())
assert resolved==snapshot and snapshot.is_dir(); print('Snapshot ready:',snapshot)
"""
    notebook["cells"][4]["source"] = before_access.splitlines(keepends=True)
    notebook["cells"][5]["source"] = download.splitlines(keepends=True)
    execution = """# Resume the single attempt; skip execution if a restored attempt already completed.
marker=json.loads((OUTPUT/'attempt_marker.json').read_text())
if marker['state']=='COMPLETE':
 print('Restored completed CORE-05 attempt',marker['attempt_id'])
else:
 command=[str(PY),'-u','-m','experiments.phase1.core05_once_only_test','--resume',
          '--output',str(OUTPUT),'--model-snapshot',str(snapshot),
          '--checkpoint-repo',HF_REPO,'--checkpoint-path','core05/checkpoint.tar.gz']
 process=subprocess.Popen(command,cwd=REPO,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
 assert process.stdout is not None
 for line in process.stdout: print(line,end='',flush=True)
 code=process.wait()
 if code: raise subprocess.CalledProcessError(code,command)
"""
    notebook["cells"][6]["source"] = execution.splitlines(keepends=True)
    return notebook


def main() -> None:
    output = ROOT / "notebooks/aether_qwen_core05_once_only_test.ipynb"
    output.write_text(json.dumps(build(), indent=1) + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
