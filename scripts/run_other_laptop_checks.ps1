param(
    [string]$Python = ".\.venv\Scripts\python.exe",
    [string]$CacheDrive = ".",
    [switch]$IncludeQwen05Tests,
    [switch]$IncludeGPT2Tests,
    [switch]$CheckMQHW1
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
    if (-not (Test-Path $Python)) { throw "Python environment not found: $Python" }
    & $Python --version
    & $Python -m pip check
    if ($LASTEXITCODE -ne 0) { throw "Python dependency check failed." }
    & $Python -m pytest tests/unit tests/integration tests/regression -ra -p no:cacheprovider --basetemp .local/portable-tests
    if ($LASTEXITCODE -ne 0) { throw "Python test suite failed." }
    Push-Location demo/frontend
    try {
        & npm.cmd ci
        if ($LASTEXITCODE -ne 0) { throw "Frontend dependency installation failed." }
        & npm.cmd test
        if ($LASTEXITCODE -ne 0) { throw "Frontend tests failed." }
        & npm.cmd run build
        if ($LASTEXITCODE -ne 0) { throw "Frontend build failed." }
    } finally { Pop-Location }
    if ($IncludeQwen05Tests) {
        $env:AETHER_RUN_REAL_MODEL_TESTS = "1"
        & $Python -m pytest tests/integration/test_hook_non_interference.py -ra -p no:cacheprovider --basetemp .local/portable-model-tests
        if ($LASTEXITCODE -ne 0) { throw "Pinned Qwen2.5-0.5B integration tests failed." }
    }
    if ($IncludeGPT2Tests) {
        $env:AETHER_RUN_CALIBRATION_MODELS = "1"
        & $Python -m pytest tests/integration/test_ioi_real_calibration.py -ra -p no:cacheprovider --basetemp .local/portable-calibration-tests
        if ($LASTEXITCODE -ne 0) { throw "Pinned GPT-2 calibration tests failed." }
    }
    if ($CheckMQHW1) {
        & $Python -m scripts.check_mq_hw1 --cache-drive $CacheDrive --output .local/portable-mq-hw1.json
        if ($LASTEXITCODE -ne 0) {
            throw "MQ-HW1 did not pass. No 1.5B model access is permitted. See .local/portable-mq-hw1.json."
        }
    }
    Write-Host "Requested portable checks passed."
} finally {
    Remove-Item Env:AETHER_RUN_REAL_MODEL_TESTS -ErrorAction SilentlyContinue
    Remove-Item Env:AETHER_RUN_CALIBRATION_MODELS -ErrorAction SilentlyContinue
    Pop-Location
}
