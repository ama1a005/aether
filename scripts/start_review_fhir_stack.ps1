param([switch]$SkipSeed)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$compose = Join-Path $root "demo\external_mcp\docker-compose.review.yml"
$python = Join-Path $root ".venv\Scripts\python.exe"

docker version *> $null
if ($LASTEXITCODE -ne 0) { throw "Docker engine is unavailable. Start Docker Desktop." }
docker compose -f $compose up -d
if ($LASTEXITCODE -ne 0) { throw "FHIR container stack failed to start." }

$fhirReady = $false
for ($attempt = 0; $attempt -lt 60; $attempt++) {
    try {
        $response = Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8080/fhir/metadata" -TimeoutSec 3
        if ($response.StatusCode -eq 200) { $fhirReady = $true; break }
    } catch { Start-Sleep -Seconds 2 }
}
if (-not $fhirReady) { throw "Local HAPI FHIR did not become ready." }
if (-not $SkipSeed) { Push-Location $root; try { & $python -m scripts.seed_review_fhir } finally { Pop-Location } }

$mcpReady = $false
for ($attempt = 0; $attempt -lt 30; $attempt++) {
    $state = docker compose -f $compose ps --status running --services
    if ($state -contains "wso2-fhir-mcp") { $mcpReady = $true; break }
    Start-Sleep -Seconds 2
}
if (-not $mcpReady) { throw "WSO2 FHIR MCP did not remain running; inspect compose logs." }
Write-Host "HAPI FHIR: http://127.0.0.1:8080/fhir"
Write-Host "WSO2 MCP:  http://127.0.0.1:8001/mcp/"
