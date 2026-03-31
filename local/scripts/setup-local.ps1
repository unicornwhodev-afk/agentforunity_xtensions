<# 
    AgentUnity — Local Setup Script (Windows)
    Sets up cloudflared, configures MCP-Unity, installs Continue.dev config,
    and installs the Unity Editor extension as a local package.
#>

param(
    [string]$UnityProjectPath,
    [string]$RunPodID,
    [string]$ApiKey
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "╔══════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║      AgentUnity — Local Setup            ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════╝" -ForegroundColor Cyan

# ── 1. Gather parameters ─────────────────────────────────────────────

if (-not $UnityProjectPath) {
    $UnityProjectPath = Read-Host "Path to your Unity project (e.g. D:\Dev\MyGame)"
}
if (-not (Test-Path $UnityProjectPath)) {
    Write-Error "Unity project path not found: $UnityProjectPath"
    exit 1
}

if (-not $RunPodID) {
    $RunPodID = Read-Host "RunPod Pod ID (e.g. abc123def, or 'skip' if not ready)"
}

if (-not $ApiKey) {
    $ApiKey = Read-Host "API Secret Key (same as server env var)"
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$LocalDir = Split-Path -Parent $ScriptDir

# ── 2. cloudflared ────────────────────────────────────────────────────

Write-Host ""
Write-Host "[1/4] Checking cloudflared..." -ForegroundColor Yellow

$cf = Get-Command cloudflared -ErrorAction SilentlyContinue
if ($cf) {
    $cfVer = & cloudflared --version 2>&1
    Write-Host "  ✓ cloudflared installed: $cfVer" -ForegroundColor Green
} else {
    Write-Host "  ⚠ cloudflared not found. Install with:" -ForegroundColor DarkYellow
    Write-Host "    winget install Cloudflare.cloudflared" -ForegroundColor White
    Write-Host "    Or download: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/" -ForegroundColor Gray
}

Write-Host "  → To expose Unity MCP to the pod, run:" -ForegroundColor Gray
Write-Host "    cloudflared tunnel --url ws://localhost:8090" -ForegroundColor Cyan
Write-Host "    Then set MCP_UNITY_WS_URL on the RunPod pod env vars." -ForegroundColor Gray

# ── 3. MCP-Unity config ──────────────────────────────────────────────

Write-Host ""
Write-Host "[2/4] Configuring MCP-Unity..." -ForegroundColor Yellow

$mcpSettingsSource = Join-Path $LocalDir "mcp-unity\McpUnitySettings.json"
$mcpSettingsDest = Join-Path $UnityProjectPath "ProjectSettings\McpUnitySettings.json"

if (Test-Path $mcpSettingsDest) {
    $existing = Get-Content $mcpSettingsDest -Raw | ConvertFrom-Json
    if ($existing.AllowRemoteConnections -eq $true) {
        Write-Host "  ✓ McpUnitySettings.json already configured with remote connections" -ForegroundColor Green
    } else {
        Write-Host "  → Updating AllowRemoteConnections to true..." -ForegroundColor Gray
        Copy-Item $mcpSettingsSource $mcpSettingsDest -Force
        Write-Host "  ✓ Updated" -ForegroundColor Green
    }
} else {
    Copy-Item $mcpSettingsSource $mcpSettingsDest -Force
    Write-Host "  ✓ Copied McpUnitySettings.json to project" -ForegroundColor Green
}

# ── 4. Unity Editor extension ────────────────────────────────────────

Write-Host ""
Write-Host "[3/4] Installing Unity Editor extension..." -ForegroundColor Yellow

$manifestPath = Join-Path $UnityProjectPath "Packages\manifest.json"
$extensionPackagePath = ($LocalDir + "\unity-extension").Replace('\', '/')

if (Test-Path $manifestPath) {
    $manifest = Get-Content $manifestPath -Raw | ConvertFrom-Json

    $pkgName = "com.agentunity.editor"
    $localRef = "file:$extensionPackagePath"

    if ($manifest.dependencies.PSObject.Properties.Name -contains $pkgName) {
        Write-Host "  ✓ Package already in manifest.json" -ForegroundColor Green
    } else {
        $manifest.dependencies | Add-Member -NotePropertyName $pkgName -NotePropertyValue $localRef -Force
        $manifest | ConvertTo-Json -Depth 10 | Set-Content $manifestPath -Encoding UTF8
        Write-Host "  ✓ Added $pkgName to manifest.json (Unity will import on next focus)" -ForegroundColor Green
    }
} else {
    Write-Host "  ⚠ Packages/manifest.json not found at $manifestPath" -ForegroundColor DarkYellow
    Write-Host "    Manually add this to your manifest.json dependencies:" -ForegroundColor Gray
    Write-Host "    `"com.agentunity.editor`": `"file:$extensionPackagePath`"" -ForegroundColor White
}

# ── 5. Continue.dev config ───────────────────────────────────────────

Write-Host ""
Write-Host "[4/4] Configuring Continue.dev..." -ForegroundColor Yellow

$continueDir = Join-Path $env:USERPROFILE ".continue"
$continueConfig = Join-Path $continueDir "config.json"
$sourceConfig = Join-Path $LocalDir "continue-config\config.json"

if (-not (Test-Path $continueDir)) {
    New-Item -ItemType Directory -Path $continueDir -Force | Out-Null
}

if ($RunPodID -ne "skip") {
    # Read source, replace placeholders, write to Continue config dir
    $configContent = Get-Content $sourceConfig -Raw
    $configContent = $configContent.Replace("RUNPOD_ID", $RunPodID)
    $configContent = $configContent.Replace("YOUR_API_SECRET_KEY", $ApiKey)

    if (Test-Path $continueConfig) {
        $backupPath = "$continueConfig.backup.$(Get-Date -Format 'yyyyMMdd-HHmmss')"
        Copy-Item $continueConfig $backupPath
        Write-Host "  → Backed up existing config to $backupPath" -ForegroundColor Gray
    }

    $configContent | Set-Content $continueConfig -Encoding UTF8
    Write-Host "  ✓ Continue config written with RunPod ID: $RunPodID" -ForegroundColor Green
} else {
    Write-Host "  → Skipped (RunPod ID not provided). Run this script again when the pod is ready." -ForegroundColor Gray
    Write-Host "    Or manually edit ~/.continue/config.json and replace RUNPOD_ID" -ForegroundColor Gray
}

# ── Done ──────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "╔══════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║           Setup Complete!                ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor White
Write-Host "  1. Focus Unity Editor → it will import the AgentUnity package" -ForegroundColor Gray
Write-Host "  2. Open: AgentUnity > Chat Window (menu bar)" -ForegroundColor Gray
Write-Host "  3. Enter the server URL (https://PODID-8080.proxy.runpod.net) and API key" -ForegroundColor Gray
Write-Host "  4. Run: cloudflared tunnel --url ws://localhost:8090" -ForegroundColor Gray
Write-Host "  5. Set MCP_UNITY_WS_URL on the pod to the cloudflared URL" -ForegroundColor Gray
Write-Host "  6. In VS Code, open Continue sidebar (Ctrl+L) to chat via the LLM" -ForegroundColor Gray
Write-Host ""
