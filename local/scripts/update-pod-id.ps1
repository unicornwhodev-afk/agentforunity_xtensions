<# 
    Update the RunPod Pod ID in Continue.dev config and Unity extension prefs.
    Run whenever your pod gets a new Pod ID (e.g. after recreation).
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$PodID,
    [string]$ApiKey
)

$continueConfig = Join-Path $env:USERPROFILE ".continue\config.json"

if (Test-Path $continueConfig) {
    $content = Get-Content $continueConfig -Raw
    # Replace any existing RunPod proxy URLs with the new Pod ID
    $content = $content -replace 'https://[a-z0-9]+-(\d{4})\.proxy\.runpod\.net', "https://${PodID}-`$1.proxy.runpod.net"
    $content | Set-Content $continueConfig -Encoding UTF8
    Write-Host "✓ Updated Continue config with new Pod ID: $PodID" -ForegroundColor Green
} else {
    Write-Host "⚠ Continue config not found at $continueConfig" -ForegroundColor Yellow
}

if ($ApiKey) {
    $content = Get-Content $continueConfig -Raw
    $content = $content -replace '"apiKey":\s*"[^"]*"', "`"apiKey`": `"$ApiKey`""
    $content | Set-Content $continueConfig -Encoding UTF8
    Write-Host "✓ Updated API key" -ForegroundColor Green
}

Write-Host ""
Write-Host "Don't forget to update the Server URL in Unity:" -ForegroundColor Gray
Write-Host "  AgentUnity > Chat Window > Connection Settings > Server URL" -ForegroundColor White
Write-Host "  → https://${PodID}-8080.proxy.runpod.net" -ForegroundColor Cyan
