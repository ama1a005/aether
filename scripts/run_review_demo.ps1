param(
    [ValidateSet("deterministic", "live_model_mcp")]
    [string]$Mode = "deterministic"
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$environment = if ($Mode -eq "live_model_mcp") { ".venv-demo-gpu" } else { ".venv" }
$python = Join-Path $root "$environment\Scripts\python.exe"
$frontend = Join-Path $root "demo\frontend"
if (-not (Test-Path $python)) { throw "Missing $environment. Follow DEMO_README.md first." }
if (-not (Test-Path (Join-Path $frontend "node_modules"))) { throw "Frontend packages missing. Run npm.cmd install in demo\frontend." }
$env:AETHER_DEMO_MODE = $Mode
Start-Process -FilePath $python -ArgumentList "-m", "demo.backend" -WorkingDirectory $root -WindowStyle Hidden
Start-Process -FilePath "npm.cmd" -ArgumentList "run", "dev" -WorkingDirectory $frontend -WindowStyle Hidden
Start-Sleep -Seconds 3
Start-Process "http://127.0.0.1:5173"
Write-Host "AETHER review demo: http://127.0.0.1:5173"
Write-Host "Backend API: http://127.0.0.1:8000/api/demo/health"
Write-Host "Backend mode: $Mode ($environment)"
