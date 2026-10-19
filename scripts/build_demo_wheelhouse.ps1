param([string]$Wheelhouse = ".local\wheelhouse", [string]$Python = "py")
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$destination = [IO.Path]::GetFullPath((Join-Path $root $Wheelhouse))
$allowedRoot = [IO.Path]::GetFullPath((Join-Path $root ".local"))
if (-not $destination.StartsWith($allowedRoot, [StringComparison]::OrdinalIgnoreCase)) { throw "Wheelhouse must be inside $allowedRoot" }
New-Item -ItemType Directory -Force -Path $destination | Out-Null
Get-ChildItem -LiteralPath $destination -File | Where-Object { $_.Extension -in @(".tmp", ".part") } | Remove-Item -Force
function Invoke-Python {
    param([string[]]$Arguments)
    if ($Python -eq "py") { & py -3.11 @Arguments } else { & $Python @Arguments }
    if ($LASTEXITCODE -ne 0) { throw "Python command failed with exit code $LASTEXITCODE" }
}
$common = @("-m", "pip", "download", "--dest", $destination, "--only-binary=:all:", "--use-feature=truststore", "--retries", "10", "--timeout", "120", "--progress-bar", "off", "--disable-pip-version-check")
Write-Host "Phase 1/4: small PyPI transport check"
Invoke-Python ($common + @("packaging==25.0"))
Write-Host "Phase 2/4: MCP SDK and dependencies"
Invoke-Python ($common + @("mcp==2.3.0"))
Write-Host "Phase 3/4: model/backend runtime dependencies"
Invoke-Python ($common + @("-r", (Join-Path $root "requirements-demo-runtime.txt")))
Write-Host "Phase 4/4: official CUDA 12.6 PyTorch wheel (no torchvision/torchaudio)"
Invoke-Python ($common + @("--no-deps", "--index-url", "https://download.pytorch.org/whl/cu126", "torch==2.8.0"))
Invoke-Python @((Join-Path $root "scripts\wheelhouse_manifest.py"), "create", $destination)
Write-Host "Complete wheelhouse: $destination"
