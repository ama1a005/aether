param([string]$Wheelhouse = ".local\wheelhouse")
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$wheelhousePath = [IO.Path]::GetFullPath((Join-Path $root $Wheelhouse))
$python = Join-Path $root ".venv-demo-gpu\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) { throw "Missing .venv-demo-gpu Python 3.11 environment" }
if (-not (Test-Path -LiteralPath (Join-Path $wheelhousePath "wheelhouse_manifest.json"))) { throw "Missing wheelhouse manifest" }
& $python (Join-Path $root "scripts\wheelhouse_manifest.py") verify $wheelhousePath
if ($LASTEXITCODE -ne 0) { throw "Wheelhouse integrity verification failed" }
& $python -m pip install --no-index --find-links $wheelhousePath -r (Join-Path $root "requirements-demo-gpu.txt") "torch==2.8.0"
if ($LASTEXITCODE -ne 0) { throw "Offline dependency installation failed" }
& $python -m pip install --no-index --no-deps --editable $root
if ($LASTEXITCODE -ne 0) { throw "Offline editable project installation failed" }
& $python (Join-Path $root "scripts\verify_demo_gpu.py")
