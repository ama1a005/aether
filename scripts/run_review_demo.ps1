$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"
$frontend = Join-Path $root "demo\frontend"
if (-not (Test-Path $python)) { throw "Missing .venv. Create the Python 3.11 environment first." }
if (-not (Test-Path (Join-Path $frontend "node_modules"))) { throw "Frontend packages missing. Run npm.cmd install in demo\frontend." }
Start-Process -FilePath $python -ArgumentList "-m", "demo.backend" -WorkingDirectory $root -WindowStyle Hidden
Start-Process -FilePath "npm.cmd" -ArgumentList "run", "dev" -WorkingDirectory $frontend -WindowStyle Hidden
Start-Sleep -Seconds 3
Start-Process "http://127.0.0.1:5173"
Write-Host "AETHER review demo: http://127.0.0.1:5173"
Write-Host "Backend API: http://127.0.0.1:8000/api/demo/health"
