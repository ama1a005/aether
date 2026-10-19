param([string]$Wheelhouse = ".local\wheelhouse")
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $root ".venv-demo-gpu\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $venvPython)) {
    & py -3.11 -m venv (Join-Path $root ".venv-demo-gpu")
    if ($LASTEXITCODE -ne 0) { throw "Python 3.11 environment creation failed" }
}
& (Join-Path $root "scripts\build_demo_wheelhouse.ps1") -Wheelhouse $Wheelhouse -Python $venvPython
if ($LASTEXITCODE -ne 0) { throw "Wheelhouse download failed; environment was not modified" }
& (Join-Path $root "scripts\install_demo_wheelhouse.ps1") -Wheelhouse $Wheelhouse
