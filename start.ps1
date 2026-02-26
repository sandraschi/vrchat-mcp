# SOTA Start Script for vrchat-mcp
# Port: 10712

$Port = 10712
$WebDir = Join-Path $PSScriptRoot "web_sota"

Write-Host "[INFO] Clearing port $Port..." -ForegroundColor Cyan
try {
    npx --yes kill-port $Port
}
catch { }

if (Test-Path $WebDir) {
    Set-Location $WebDir
    Write-Host "[INFO] Starting SOTA Webapp on port $Port..." -ForegroundColor Green
    npm run dev -- --port $Port --host
}
else {
    Write-Host "[ERROR] SOTA Webapp directory not found: $WebDir" -ForegroundColor Red
}
