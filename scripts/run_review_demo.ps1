param(
    [ValidateSet("real_fhir_mcp_deterministic", "real_fhir_mcp_qwen", "mock_deterministic", "replay")]
    [string]$Mode = "real_fhir_mcp_deterministic"
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$environment = if ($Mode -eq "real_fhir_mcp_qwen") { ".venv-demo-gpu" } else { ".venv" }
$python = Join-Path $root "$environment\Scripts\python.exe"
$frontend = Join-Path $root "demo\frontend"
if (-not (Test-Path $python)) { throw "Missing $environment. Follow DEMO_README.md first." }
if (-not (Test-Path (Join-Path $frontend "node_modules"))) { throw "Frontend packages missing. Run npm.cmd install in demo\frontend." }
$env:AETHER_DEMO_MODE = $Mode
if ($Mode -like "real_fhir_mcp*") {
    & (Join-Path $root "scripts\start_review_fhir_stack.ps1")
}
Start-Process -FilePath $python -ArgumentList "-m", "demo.backend" -WorkingDirectory $root -WindowStyle Hidden
Start-Process -FilePath "npm.cmd" -ArgumentList "run", "dev" -WorkingDirectory $frontend -WindowStyle Hidden
Start-Sleep -Seconds 3
Start-Process "http://127.0.0.1:5173"
Write-Host "AETHER review demo: http://127.0.0.1:5173"
Write-Host "Backend API: http://127.0.0.1:8000/api/demo/health"
Write-Host "Backend mode: $Mode ($environment)"
