# start_appium.ps1 — Stage 2 helper for the 7zip-slice-verify-novawindows skill.
#
# Starts the Appium server with the NovaWindows driver installed.
# Enables the 'power_shell' insecure feature so tests can run PowerShell scripts
# through the driver (used by wait_for_new_window_powershell fallback).
#
# Usage:
#   .\start_appium.ps1                # foreground — Ctrl+C to stop
#   .\start_appium.ps1 -Background   # background process, writes to .\appium.log
#   .\start_appium.ps1 -Port 4724    # use alternate port

param(
    [int]    $Port       = 4723,
    [switch] $Background
)

# ── Pre-flight checks ────────────────────────────────────────────────────────
function Assert-Command($name, $hint) {
    if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
        Write-Error "Required command '$name' not found. $hint"
        exit 1
    }
}

Assert-Command "node"   "Install Node.js 18+ from https://nodejs.org"
Assert-Command "appium" "Run: npm install -g appium"

$driverList = appium driver list --installed 2>&1
if (-not ($driverList | Select-String "novawindows")) {
    Write-Error "NovaWindows driver not installed. Run: appium driver install --source=npm appium-novawindows-driver"
    exit 1
}

# ── Appium arguments ─────────────────────────────────────────────────────────
$args = @(
    "--port", $Port,
    "--allow-insecure", "novawindows:power_shell",   # Appium 3.x format: <driver>:<feature>
    "--log-timestamp"
)

Write-Host "Starting Appium $( (appium --version 2>&1).Trim() ) on port $Port ..."
Write-Host "NovaWindows driver: $( $driverList | Select-String 'novawindows' )"
Write-Host ""

if ($Background) {
    $logFile    = Join-Path $PSScriptRoot "appium.log"
    $logFileErr = Join-Path $PSScriptRoot "appium-err.log"
    Write-Host "Running in background. Log: $logFile"
    $proc = Start-Process `
        -FilePath "cmd.exe" `
        -ArgumentList (@("/c", "appium") + $args) `
        -NoNewWindow `
        -RedirectStandardOutput $logFile `
        -RedirectStandardError  $logFileErr `
        -PassThru
    Write-Host "Appium PID: $($proc.Id)"

    # Wait up to 20 seconds for the server to be ready
    $deadline = (Get-Date).AddSeconds(20)
    $ready    = $false
    while ((Get-Date) -lt $deadline -and -not $ready) {
        Start-Sleep -Milliseconds 500
        if (Test-Path $logFile) {
            $content = Get-Content $logFile -Raw -ErrorAction SilentlyContinue
            if ($content -match "listener started") {
                $ready = $true
            }
        }
    }

    if ($ready) {
        Write-Host "Appium ready on http://127.0.0.1:$Port"
    } else {
        Write-Warning "Appium did not report ready within 20s. Check $logFile"
    }
} else {
    Write-Host "Press Ctrl+C to stop."
    Write-Host ""
    cmd.exe /c appium @args
}
