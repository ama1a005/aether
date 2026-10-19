$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $root ".venv-demo-gpu\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    & py -3.11 -m venv (Join-Path $root ".venv-demo-gpu")
}

& $venvPython -m pip install --use-feature=truststore "torch==2.8.0" --index-url https://download.pytorch.org/whl/cu128
& $venvPython -m pip install --use-feature=truststore -r (Join-Path $root "requirements-demo-gpu.txt")
& $venvPython (Join-Path $root "scripts\verify_demo_gpu.py")
