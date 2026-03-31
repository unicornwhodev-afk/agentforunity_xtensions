<# 
    AgentUnity - Test connectivity to RunPod services
    Run after pod is up + cloudflared tunnel active
#>

param(
    [string]$RunPodID
)

if (-not $RunPodID) {
    $RunPodID = Read-Host "RunPod Pod ID (e.g. abc123def)"
}

$proxyBase = "https://${RunPodID}"

Write-Host ""
Write-Host "Testing connectivity to AgentUnity RunPod (Pod ID: $RunPodID)..." -ForegroundColor Cyan
Write-Host ""

$services = @(
    @{ Name = "FastAPI (orchestrator)"; Url = "${proxyBase}-8080.proxy.runpod.net/api/v1/health" },
    @{ Name = "vLLM LLM (32B)";        Url = "${proxyBase}-8000.proxy.runpod.net/v1/models" },
    @{ Name = "vLLM Vision (7B)";      Url = "${proxyBase}-8001.proxy.runpod.net/v1/models" },
    @{ Name = "Embeddings (BGE-M3)";   Url = "${proxyBase}-8002.proxy.runpod.net/health" },
    @{ Name = "Reranker (BGE)";        Url = "${proxyBase}-8003.proxy.runpod.net/health" },
    @{ Name = "Qdrant";                Url = "${proxyBase}-6333.proxy.runpod.net/collections" }
)

$allOk = $true

foreach ($svc in $services) {
    try {
        $response = Invoke-WebRequest -Uri $svc.Url -TimeoutSec 10 -UseBasicParsing -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Host ("  [OK] " + $svc.Name) -ForegroundColor Green -NoNewline
            Write-Host (" - " + $svc.Url) -ForegroundColor DarkGray
        }
        else {
            Write-Host ("  [WARN] " + $svc.Name + " - HTTP " + $response.StatusCode) -ForegroundColor Yellow
            $allOk = $false
        }
    }
    catch {
        $statusCode = 0
        if ($_.Exception.Response) {
            $statusCode = [int]$_.Exception.Response.StatusCode
        }
        if ($statusCode -eq 401 -or $statusCode -eq 403) {
            Write-Host ("  [OK] " + $svc.Name + " (auth required)") -ForegroundColor Green -NoNewline
            Write-Host (" - " + $svc.Url) -ForegroundColor DarkGray
        }
        else {
            Write-Host ("  [FAIL] " + $svc.Name) -ForegroundColor Red -NoNewline
            Write-Host (" - " + $_.Exception.Message) -ForegroundColor DarkGray
            $allOk = $false
        }
    }
}

# Test MCP-Unity local
Write-Host ""
Write-Host "Testing local MCP-Unity (port 8090)..." -ForegroundColor Cyan

$mcpOk = $false
$listening = Get-NetTCPConnection -LocalPort 8090 -State Listen -ErrorAction SilentlyContinue
if ($listening) {
    $proc = Get-Process -Id $listening.OwningProcess -ErrorAction SilentlyContinue
    Write-Host ("  [OK] MCP-Unity listening on port 8090 (process: " + $proc.ProcessName + ")") -ForegroundColor Green
    $mcpOk = $true
}
if (-not $mcpOk) {
    Write-Host "  [FAIL] MCP-Unity not listening on port 8090" -ForegroundColor Red
    Write-Host "    -> Make sure Unity Editor is open with the mcp-unity package" -ForegroundColor Gray
    $allOk = $false
}

# Test cloudflared
Write-Host ""
Write-Host "Checking cloudflared..." -ForegroundColor Cyan

$cf = Get-Command cloudflared -ErrorAction SilentlyContinue
if ($cf) {
    Write-Host "  [OK] cloudflared installed" -ForegroundColor Green
    Write-Host "    To expose Unity MCP: cloudflared tunnel --url ws://localhost:8090" -ForegroundColor Gray
}
else {
    $cfPath = Join-Path $env:LOCALAPPDATA "cloudflared\cloudflared.exe"
    if (Test-Path $cfPath) {
        Write-Host "  [OK] cloudflared installed (local)" -ForegroundColor Green
    }
    else {
        Write-Host "  [WARN] cloudflared not found in PATH" -ForegroundColor Yellow
        $allOk = $false
    }
}

# Summary
Write-Host ""
if ($allOk) {
    Write-Host "All services are UP! You are ready to use AgentUnity." -ForegroundColor Green
}
else {
    Write-Host "Some services are DOWN. Check the errors above." -ForegroundColor Yellow
}
Write-Host ""
