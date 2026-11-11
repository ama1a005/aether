"""Validate notebook setup behavior without provisioning a remote environment."""
import json
import hashlib
import ast
import shutil
import subprocess
from pathlib import Path


def test_notebook_sources_compile_and_locks_include_demo(tmp_path):
    root = Path(__file__).resolve().parents[2]
    notebook = json.loads((root / 'notebooks/aether_kaggle_t4_setup.ipynb').read_text(encoding='utf-8'))
    sources = [''.join(cell['source']) for cell in notebook['cells']
               if cell['cell_type'] == 'code']
    for index, source in enumerate(sources):
        compile(source, f'cell-{index}', 'exec')
    scope = {'REPO': root, 'WORK': tmp_path}
    lock_cell = next(source for source in sources if '# Make a Linux/CUDA' in source)
    exec(compile(lock_cell, 'lock-cell', 'exec'), scope)
    base = scope['kaggle_lock'].read_text()
    demo = scope['kaggle_demo_lock'].read_text()
    assert 'torch==' not in base
    assert 'fastapi==' in demo and 'mcp==' in demo
    assert 'pywin32==' not in demo and '-r requirements-lock.txt' not in demo
    assert len(demo.splitlines()) > 20
    assert "os.environ['MPLBACKEND'] = 'Agg'" in sources[0]
    assert any('pip==25.3' in source for source in sources)


def test_notebook_archive_contains_logs_and_verified_hashes(tmp_path):
    root = Path(__file__).resolve().parents[2]
    notebook = json.loads((root / 'notebooks/aether_kaggle_t4_setup.ipynb').read_text(encoding='utf-8'))
    source = next(''.join(c['source']) for c in notebook['cells']
                  if '# Create a single downloadable archive' in ''.join(c['source']))
    repo = tmp_path / 'repository'
    repo.mkdir()
    subprocess.run(['git', 'init', str(repo)], check=True, capture_output=True)
    output = tmp_path / 'output'
    output.mkdir()
    (output / 'training.log').write_text('executed fixture')
    locks = [tmp_path / name for name in ('base.txt', 'demo.txt')]
    for lock in locks:
        lock.write_text('fixture==1\n')
    scope = dict(Path=Path, REPO=repo, WORK=tmp_path, OUTPUT_ROOT=output,
                 subprocess=subprocess, shutil=shutil, hashlib=hashlib, json=json,
                 kaggle_lock=locks[0], kaggle_demo_lock=locks[1])
    exec(compile(source, 'archive-cell', 'exec'), scope)
    assert scope['sha256'] == hashlib.sha256(scope['archive'].read_bytes()).hexdigest()
    import zipfile
    with zipfile.ZipFile(scope['archive']) as archive:
        hashes = json.loads(archive.read('artifact_hashes.json'))
        for name, digest in hashes.items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == digest
        assert 'training.log' in hashes


def test_qwen_qualification_notebook_is_pinned_and_runs_gates_in_order():
    root = Path(__file__).resolve().parents[2]
    notebook_path = root / 'notebooks/aether_qwen_qualification_cpu.ipynb'
    notebook = json.loads(notebook_path.read_text(encoding='utf-8'))
    code_cells = [''.join(cell['source']) for cell in notebook['cells']
                  if cell['cell_type'] == 'code']
    for index, source in enumerate(code_cells):
        ast.parse(source, filename=f'qwen-notebook-cell-{index}')
    cell_ids = [cell['id'] for cell in notebook['cells']]
    assert len(cell_ids) == len(set(cell_ids))
    assert all(cell['outputs'] == [] and cell['execution_count'] is None
               for cell in notebook['cells'] if cell['cell_type'] == 'code')
    preflight = next(i for i, source in enumerate(code_cells) if '--preflight-only' in source)
    download = next(i for i, source in enumerate(code_cells) if 'snapshot_download' in source)
    campaign = next(i for i, source in enumerate(code_cells)
                    if 'paired_trace.run_model_qualification' in source and '--preflight-only' not in source)
    assert preflight < download < campaign
    combined = '\n'.join(code_cells)
    assert '989aa7980e4cf806f80c7fef2b1adb7bc71aa306' in combined
    assert 'torch==2.14.1' in combined and 'download.pytorch.org/whl/cpu' in combined
    assert 'SET_AFTER_QUALIFICATION_RUNNER_COMMIT' not in combined


def test_qwen_instrumentation_notebook_is_pinned_bounded_and_ordered():
    root = Path(__file__).resolve().parents[2]
    notebook_path = root / 'notebooks/aether_qwen_instrumentation_acceptance_cpu.ipynb'
    notebook = json.loads(notebook_path.read_text(encoding='utf-8'))
    code_cells = [''.join(cell['source']) for cell in notebook['cells']
                  if cell['cell_type'] == 'code']
    for index, source in enumerate(code_cells):
        ast.parse(source, filename=f'instrumentation-notebook-cell-{index}')
    assert len({cell['id'] for cell in notebook['cells']}) == len(notebook['cells'])
    assert all(cell['outputs'] == [] and cell['execution_count'] is None
               for cell in notebook['cells'] if cell['cell_type'] == 'code')
    preflight = next(i for i, source in enumerate(code_cells)
                     if '--preflight-only' in source)
    download = next(i for i, source in enumerate(code_cells)
                    if 'snapshot_download' in source)
    execution = next(i for i, source in enumerate(code_cells)
                     if "run_logged('qwen-instrumentation-acceptance'" in source)
    archive = next(i for i, source in enumerate(code_cells)
                   if 'archive_contents.json' in source)
    assert preflight < download < execution < archive
    combined = '\n'.join(code_cells)
    assert '989aa7980e4cf806f80c7fef2b1adb7bc71aa306' in combined
    assert 'torch==2.14.1' in combined and 'download.pytorch.org/whl/cpu' in combined
    assert 'SET_AFTER_INSTRUMENTATION_ACCEPTANCE_COMMIT' not in combined
    assert 'AETHER_RUN_REAL_MODEL_TESTS' in combined
    assert "os.environ.pop(name,None)" in combined


def test_qwen_development_capture_notebook_is_pinned_and_ordered():
    root = Path(__file__).resolve().parents[2]
    notebook = json.loads(
        (root / 'notebooks/aether_qwen_development_capture_cpu.ipynb').read_text(encoding='utf-8')
    )
    code_cells = [''.join(cell['source']) for cell in notebook['cells']
                  if cell['cell_type'] == 'code']
    for index, source in enumerate(code_cells):
        ast.parse(source, filename=f'capture-notebook-cell-{index}')
    assert len({cell['id'] for cell in notebook['cells']}) == len(notebook['cells'])
    assert all(cell['outputs'] == [] and cell['execution_count'] is None
               for cell in notebook['cells'] if cell['cell_type'] == 'code')
    preflight = next(i for i, source in enumerate(code_cells) if '--preflight-only' in source)
    download = next(i for i, source in enumerate(code_cells) if 'snapshot_download' in source)
    capture = next(i for i, source in enumerate(code_cells)
                   if "run_logged('qwen-development-capture'" in source)
    archive = next(i for i, source in enumerate(code_cells) if 'archive_contents.json' in source)
    assert preflight < download < capture < archive
    combined = '\n'.join(code_cells)
    assert '50c9d1b01304cdb9aabf313cb1d7f35b05f6a618' in combined
    assert "git','fetch','--no-tags','origin','lm" in combined
    assert "aether-qwen-development-capture-corrected" in combined
    assert "subprocess.Popen" in combined
    assert "print(line,end='',flush=True)" in combined
    assert '989aa7980e4cf806f80c7fef2b1adb7bc71aa306' in combined
    assert 'torch==2.14.1' in combined and 'download.pytorch.org/whl/cpu' in combined
    assert 'instrumentation.run_qwen_development_capture' in combined


def test_qwen_qci_notebook_is_pinned_ordered_and_locked():
    root = Path(__file__).resolve().parents[2]
    notebook = json.loads(
        (root / 'notebooks/aether_qwen_causal_interventions_cpu.ipynb').read_text(encoding='utf-8')
    )
    code_cells = [''.join(cell['source']) for cell in notebook['cells']
                  if cell['cell_type'] == 'code']
    for index, source in enumerate(code_cells):
        ast.parse(source, filename=f'qci-notebook-cell-{index}')
    assert len(notebook['cells']) == 11
    assert len({cell['id'] for cell in notebook['cells']}) == len(notebook['cells'])
    assert all(cell['outputs'] == [] and cell['execution_count'] is None
               for cell in notebook['cells'] if cell['cell_type'] == 'code')
    preflight = next(i for i, source in enumerate(code_cells) if '--preflight-only' in source)
    download = next(i for i, source in enumerate(code_cells) if 'snapshot_download' in source)
    execution = next(i for i, source in enumerate(code_cells)
                     if "run_logged('qwen-causal-interventions'" in source)
    archive = next(i for i, source in enumerate(code_cells) if 'archive_contents.json' in source)
    assert preflight < download < execution < archive
    combined = '\n'.join(code_cells)
    assert '0e8a616aedd8a7a5caf2af5b34d9170bf9f114fc' in combined
    assert '989aa7980e4cf806f80c7fef2b1adb7bc71aa306' in combined
    assert 'instrumentation.run_qwen_causal_interventions' in combined
    assert 'tests/unit/test_qci_execution.py' in combined
    assert 'aether-qwen-qci-results.tar.gz' in combined
    assert 'subprocess.Popen' in combined
