param(
    [ValidateSet("real_fhir_mcp_deterministic", "mock_deterministic", "replay")]
    [string]$Mode = "real_fhir_mcp_deterministic",
    [switch]$NoBrowser
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$environment = ".venv"
$python = Join-Path $root "$environment\Scripts\python.exe"
$frontend = Join-Path $root "demo\frontend"
if (-not (Test-Path $python)) { throw "Missing $environment. Follow DEMO_README.md first." }
if (-not (Test-Path (Join-Path $frontend "node_modules"))) { throw "Frontend packages missing. Run npm.cmd install in demo\frontend." }
$env:AETHER_DEMO_MODE = $Mode
$env:AETHER_DEMO_INSTANCE_ID = [guid]::NewGuid().ToString()
$listeners = @(Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue)
if ($listeners.Count) {
    $owners = ($listeners.OwningProcess | Select-Object -Unique) -join ", "
    throw "Port 8000 is occupied by PID(s) $owners. Stop your previous demo server, then retry. No processes were stopped."
}
Push-Location $frontend
try {
    & npm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw "Frontend build failed; demo was not started." }
} finally { Pop-Location }
if ($Mode -like "real_fhir_mcp*") {
    & (Join-Path $root "scripts\start_review_fhir_stack.ps1")
}
$logDir = Join-Path $root ".local\demo"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$process = Start-Process -FilePath $python -ArgumentList "-m", "demo.backend" -WorkingDirectory $root -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logDir "backend.stdout.log") -RedirectStandardError (Join-Path $logDir "backend.stderr.log")
$ready = $false
for ($attempt = 0; $attempt -lt 30; $attempt++) {
    $process.Refresh()
    if ($process.HasExited) { throw "Demo backend exited. Inspect $logDir\backend.stderr.log" }
    try {
        $health = Invoke-RestMethod "http://127.0.0.1:8000/api/demo/health" -TimeoutSec 2
        if ($health.service -eq "aether-review-demo" -and $health.instance_id -eq $env:AETHER_DEMO_INSTANCE_ID -and $health.case_count -eq 12) { $ready = $true; break }
    } catch { Write-Verbose "Waiting for backend: $_" }
    Start-Sleep -Seconds 1
}
if (-not $ready) { throw "Backend did not pass health verification. PID $($process.Id); logs: $logDir" }
# Serve the built UI and API together; no stale Vite proxy or second port.
$url = "http://127.0.0.1:8000/?mode=$Mode"
if (-not $NoBrowser) { Start-Process $url }
Write-Host "AETHER review demo: $url"
Write-Host "Backend PID: $($process.Id). Logs: $logDir"
Write-Host "Stop this demo when finished: Stop-Process -Id $($health.process_id)"
Write-Host "Backend API: http://127.0.0.1:8000/api/demo/health"
Write-Host "Backend mode: $Mode ($environment)"
